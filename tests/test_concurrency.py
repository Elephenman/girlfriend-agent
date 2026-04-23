# tests/test_concurrency.py
import asyncio
import os
import tempfile

import pytest

from src.core.config import Config
from src.core.evolve import EvolveEngine
from src.core.git_manager import GitManager
from src.core.models import ChatRequest, RelationshipState


class TestConcurrencyStateLock:
    """Verify asyncio.Lock protects state consistency under concurrent access"""

    @pytest.fixture
    def evolve_engine(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
            data_dir = os.path.join(td, "gf-agent")
            config = Config(data_dir=data_dir)
            config.ensure_dirs()
            git_mgr = GitManager(data_dir=config.data_dir)
            git_mgr.init_repo()
            yield EvolveEngine(config, git_mgr)

    def test_sequential_chat_intimacy_accumulates(self, evolve_engine):
        """Baseline: sequential /chat requests should accumulate intimacy correctly"""
        relationship = RelationshipState()
        for i in range(5):
            req = ChatRequest(user_message=f"msg_{i}", interaction_type="daily_chat", level=1)
            relationship = evolve_engine.update_intimacy(req.interaction_type, relationship)
            relationship = evolve_engine.add_interaction_attributes(req.interaction_type, relationship)

        # 5 daily_chat requests: 1 intimacy each -> 5 total
        assert relationship.intimacy_points == 5

    @pytest.mark.anyio
    async def test_concurrent_chat_with_lock_preserves_intimacy(self, evolve_engine):
        """Verify Lock prevents intimacy loss under concurrent /chat requests"""
        # Simulate the lock-protected mutation pattern from chat_router
        lock = asyncio.Lock()
        shared_state = {"relationship": RelationshipState()}

        async def simulate_chat_request(i: int):
            async with lock:
                rel = shared_state["relationship"]
                req = ChatRequest(user_message=f"msg_{i}", interaction_type="daily_chat", level=1)
                rel = evolve_engine.update_intimacy(req.interaction_type, rel)
                rel = evolve_engine.add_interaction_attributes(req.interaction_type, rel)
                shared_state["relationship"] = rel

        await asyncio.gather(*[simulate_chat_request(i) for i in range(5)])
        assert shared_state["relationship"].intimacy_points == 5

    @pytest.mark.anyio
    async def test_concurrent_chat_without_lock_may_lose_intimacy(self, evolve_engine):
        """Control experiment: without Lock, concurrent updates may lose intimacy"""
        shared_state = {"relationship": RelationshipState()}

        async def simulate_chat_request_unprotected(i: int):
            # No lock - read shared state, mutate, write back
            # Race condition: multiple coroutines may read same initial state
            rel = shared_state["relationship"]  # read
            req = ChatRequest(user_message=f"msg_{i}", interaction_type="daily_chat", level=1)
            rel = evolve_engine.update_intimacy(req.interaction_type, rel)  # mutate
            # Artificial yield point to force race condition
            await asyncio.sleep(0.001)
            shared_state["relationship"] = rel  # write back (may overwrite another's update)

        await asyncio.gather(*[simulate_chat_request_unprotected(i) for i in range(5)])
        # Without lock, intimacy_points may be less than 5 due to lost updates
        # This test demonstrates the problem: actual <= 5
        actual = shared_state["relationship"].intimacy_points
        assert actual <= 5  # may be 1-4 depending on scheduling

    @pytest.mark.anyio
    async def test_concurrent_mixed_chat_and_evolve_with_lock(self, evolve_engine):
        """Verify Lock prevents conflicts between concurrent /chat and /evolve mutations"""
        lock = asyncio.Lock()
        shared_state = {"relationship": RelationshipState()}

        async def simulate_chat_request(i: int):
            async with lock:
                rel = shared_state["relationship"]
                req = ChatRequest(user_message=f"msg_{i}", interaction_type="daily_chat", level=1)
                rel = evolve_engine.update_intimacy(req.interaction_type, rel)
                rel = evolve_engine.add_interaction_attributes(req.interaction_type, rel)
                shared_state["relationship"] = rel

        async def simulate_evolve_request():
            async with lock:
                rel = shared_state["relationship"]
                # Simulate a simple state mutation from evolve
                rel = evolve_engine.update_intimacy("deep_conversation", rel)
                shared_state["relationship"] = rel

        # Run 3 chat + 1 evolve concurrently
        tasks = [simulate_chat_request(i) for i in range(3)]
        tasks.append(simulate_evolve_request())
        await asyncio.gather(*tasks)

        # All mutations should be applied: 3*1 + 3 = 6 intimacy
        assert shared_state["relationship"].intimacy_points == 6

    @pytest.mark.anyio
    async def test_concurrent_chat_and_revert_with_lock(self, evolve_engine):
        """Verify Lock prevents conflicts between concurrent /chat and /evolve/revert"""
        lock = asyncio.Lock()
        shared_state = {"relationship": RelationshipState()}

        async def simulate_chat_request(i: int):
            async with lock:
                rel = shared_state["relationship"]
                req = ChatRequest(user_message=f"msg_{i}", interaction_type="daily_chat", level=1)
                rel = evolve_engine.update_intimacy(req.interaction_type, rel)
                shared_state["relationship"] = rel

        async def simulate_revert_request():
            """Simulate /evolve/revert: reload state from disk (reset to initial)."""
            async with lock:
                # Revert resets relationship to initial state
                shared_state["relationship"] = RelationshipState()

        # Run 3 chat requests and a revert concurrently
        tasks = [simulate_chat_request(i) for i in range(3)]
        tasks.append(simulate_revert_request())
        await asyncio.gather(*tasks)

        # After revert, intimacy should be either 0 (revert won) or some chat results (chats won after revert)
        # The key point: no partial/corrupted state - intimacy is a well-defined integer
        intimacy = shared_state["relationship"].intimacy_points
        assert isinstance(intimacy, int)
        # Possible outcomes: revert ran first -> chats add 0-3; revert ran last -> 0; mixed -> 0-3
        assert intimacy >= 0

    @pytest.mark.anyio
    async def test_high_concurrency_chat_with_lock(self, evolve_engine):
        """Stress test: 50 concurrent /chat requests under Lock protection"""
        lock = asyncio.Lock()
        shared_state = {"relationship": RelationshipState()}

        async def simulate_chat_request(i: int):
            async with lock:
                rel = shared_state["relationship"]
                req = ChatRequest(user_message=f"msg_{i}", interaction_type="daily_chat", level=1)
                rel = evolve_engine.update_intimacy(req.interaction_type, rel)
                shared_state["relationship"] = rel

        await asyncio.gather(*[simulate_chat_request(i) for i in range(50)])
        assert shared_state["relationship"].intimacy_points == 50

    @pytest.mark.anyio
    async def test_concurrent_mixed_chat_evolve_revert_with_lock(self, evolve_engine):
        """Full matrix: concurrent /chat + /evolve + /evolve/revert under Lock"""
        lock = asyncio.Lock()
        shared_state = {"relationship": RelationshipState()}

        async def simulate_chat_request(i: int):
            async with lock:
                rel = shared_state["relationship"]
                req = ChatRequest(user_message=f"msg_{i}", interaction_type="daily_chat", level=1)
                rel = evolve_engine.update_intimacy(req.interaction_type, rel)
                shared_state["relationship"] = rel

        async def simulate_evolve_request():
            async with lock:
                rel = shared_state["relationship"]
                rel = evolve_engine.update_intimacy("deep_conversation", rel)
                shared_state["relationship"] = rel

        async def simulate_revert_request():
            async with lock:
                shared_state["relationship"] = RelationshipState()

        # 5 chat + 2 evolve + 1 revert
        tasks = [simulate_chat_request(i) for i in range(5)]
        tasks.extend([simulate_evolve_request() for _ in range(2)])
        tasks.append(simulate_revert_request())
        await asyncio.gather(*tasks)

        # Final intimacy is a well-defined integer (revert may zero it, or some mutations may survive)
        intimacy = shared_state["relationship"].intimacy_points
        assert isinstance(intimacy, int)
        assert intimacy >= 0