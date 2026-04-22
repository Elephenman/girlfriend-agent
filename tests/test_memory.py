import json
import os

import pytest

from src.core.config import Config
from src.core.memory import MemoryEngine
from src.core.models import RelationshipState, SessionMemory


@pytest.fixture
def memory_engine(temp_data_dir):
    config = Config(data_dir=temp_data_dir)
    config.ensure_dirs()
    engine = MemoryEngine(config)
    return engine


class TestMemoryEngineLongTerm:
    def test_store_and_search(self, memory_engine):
        memory_engine.store_memory("我喜欢猫", "fact")
        memory_engine.store_memory("我喜欢狗", "fact")
        memory_engine.store_memory("今天天气不错", "event")

        results = memory_engine.search_memories("猫", n=2)
        assert len(results) >= 1
        assert any("猫" in r["content"] for r in results)

    def test_store_with_metadata(self, memory_engine):
        memory_engine.store_memory("用户生日是5月", "fact", metadata={"importance": "high"})
        results = memory_engine.search_memories("生日", n=1)
        assert len(results) >= 1

    def test_weight_computation(self, memory_engine):
        w = memory_engine.compute_weight(days=0, access_count=0)
        assert w == 1.0  # sqrt(1) * exp(0) = 1.0

        w_old = memory_engine.compute_weight(days=30, access_count=0)
        w_new = memory_engine.compute_weight(days=0, access_count=0)
        assert w_old < w_new  # older → lower weight

    def test_weight_increases_with_access(self, memory_engine):
        w_no_access = memory_engine.compute_weight(days=10, access_count=0)
        w_accessed = memory_engine.compute_weight(days=10, access_count=10)
        assert w_accessed > w_no_access


class TestMemoryEngineShortTerm:
    def test_save_and_load_session(self, memory_engine):
        session = SessionMemory(
            conversation_id="conv-001",
            topics=["日常", "工作"],
            emotion_summary="开心",
            interaction_type="daily_chat",
            intimacy_gained=1,
        )
        memory_engine.save_session(session)
        loaded = memory_engine.load_recent_sessions(count=1)
        assert len(loaded) >= 1
        assert loaded[0].conversation_id == "conv-001"

    def test_cleanup_old_sessions(self, memory_engine):
        for i in range(15):
            session = SessionMemory(
                conversation_id=f"conv-{i:03d}",
                topics=["test"],
            )
            memory_engine.save_session(session)

        memory_engine.cleanup_old_sessions(keep=10)
        loaded = memory_engine.load_recent_sessions(count=20)
        assert len(loaded) <= 10


class TestMemoryEngineInjection:
    def test_level_1_returns_limited_context(self, memory_engine):
        for i in range(10):
            memory_engine.store_memory(f"记忆内容{i}", "fact")

        state = RelationshipState(current_level=1)
        context = memory_engine.get_injection_context("记忆", level=1, state=state)
        assert len(context["memory_fragments"]) <= 3

    def test_level_2_returns_more_context(self, memory_engine):
        for i in range(20):
            memory_engine.store_memory(f"记忆内容{i}", "fact")

        state = RelationshipState(current_level=2)
        context = memory_engine.get_injection_context("记忆", level=2, state=state)
        assert len(context["memory_fragments"]) <= 8

    def test_level_3_returns_most_context(self, memory_engine):
        for i in range(30):
            memory_engine.store_memory(f"记忆内容{i}", "fact")

        state = RelationshipState(current_level=3)
        context = memory_engine.get_injection_context("记忆", level=3, state=state)
        assert len(context["memory_fragments"]) <= 15


class TestMemoryEngineDecay:
    def test_decay_all_weights(self, memory_engine):
        memory_engine.store_memory("test decay", "fact")
        memory_engine.decay_all_weights()
        # After decay, just verify no crash
        results = memory_engine.search_memories("decay", n=1)
        assert isinstance(results, list)
