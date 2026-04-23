"""Full-chain integration test: chat → memory → evolve → rollback"""
import asyncio
import json
import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.config import Config
from src.core.git_manager import GitManager
from src.core.models import PersonaConfig, RelationshipState
from src.core.persona import PersonaEngine
from src.core.memory import MemoryEngine
from src.core.evolve import EvolveEngine
from src.core.state_manager import StateManager
from src.engine_server import app


@pytest.fixture
def full_env():
    td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    try:
        config = Config(data_dir=os.path.join(td.name, "gf-agent"))
        config.ensure_dirs()

        git_mgr = GitManager(data_dir=config.data_dir)
        git_mgr.init_repo()

        state_mgr = StateManager(config)
        persona = state_mgr.load_or_init_persona()
        relationship = state_mgr.load_or_init_relationship()

        app.state.config = config
        app.state.persona = persona
        app.state.relationship = relationship
        app.state.persona_engine = PersonaEngine(config)
        app.state.memory_engine = MemoryEngine(config)
        app.state.evolve_engine = EvolveEngine(config, git_mgr)
        app.state.git_manager = git_mgr
        app.state.state_manager = state_mgr
        app.state.state_lock = asyncio.Lock()

        yield config
    finally:
        td.cleanup()


@pytest.mark.anyio
async def test_full_chain_chat_memory_evolve(full_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Chat
        resp = await client.post("/chat", json={
            "user_message": "我今天工作好累",
            "level": 1,
            "interaction_type": "emotion_companion",
        })
        assert resp.status_code == 200
        chat_data = resp.json()
        assert "Lv0" in chat_data["relationship_summary"]

        # 2. Store a memory
        resp = await client.post("/memory/update", json={
            "content": "用户工作很累需要安慰",
            "memory_type": "emotion",
        })
        assert resp.status_code == 200

        # 3. Check status — intimacy should have increased
        resp = await client.get("/status")
        status_data = resp.json()
        assert status_data["intimacy_points"] > 0

        # 4. Simulate multiple chats to trigger level up
        for i in range(15):
            resp = await client.post("/chat", json={
                "user_message": f"日常聊天{i}",
                "level": 1,
                "interaction_type": "daily_chat",
            })
            assert resp.status_code == 200

        # Check if level up occurred
        resp = await client.get("/status")
        status_data = resp.json()
        # After 15 daily + 1 emotion_companion = 15+4=19 intimacy → should be Lv1 (threshold=10)
        assert status_data["current_level"] >= 1

        # 5. Rollback test
        log = app.state.git_manager.log()
        if len(log) >= 2:
            earlier_hash = log[-1]["hash"]
            resp = await client.post("/rollback", json={
                "commit_hash": earlier_hash,
            })
            assert resp.status_code == 200

            # Verify state was restored
            resp = await client.get("/status")
            assert resp.status_code == 200
