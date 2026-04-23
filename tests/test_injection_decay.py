import math
from datetime import datetime, timedelta
from unittest.mock import MagicMock

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


# ─── compute_weight ───────────────────────────────────────────────


class TestComputeWeight:
    def test_default_decay_lambda(self, memory_engine):
        """默认 decay_lambda=0.1 时行为不变"""
        w = memory_engine.compute_weight(days=0, access_count=0)
        assert w == pytest.approx(1.0)  # sqrt(1) * exp(0)

    def test_custom_decay_lambda(self, memory_engine):
        """自定义 decay_lambda"""
        # lambda=0.2, days=10 => exp(-2) ≈ 0.1353
        w = memory_engine.compute_weight(days=10, access_count=0, decay_lambda=0.2)
        expected = 1.0 * math.exp(-0.2 * 10)
        assert w == pytest.approx(expected, rel=1e-6)

    def test_older_memories_weight_lower(self, memory_engine):
        w_new = memory_engine.compute_weight(days=0, access_count=0)
        w_old = memory_engine.compute_weight(days=30, access_count=0)
        assert w_old < w_new

    def test_more_access_higher_weight(self, memory_engine):
        w_none = memory_engine.compute_weight(days=10, access_count=0)
        w_many = memory_engine.compute_weight(days=10, access_count=10)
        assert w_many > w_none

    def test_uses_config_lambda_by_default(self, memory_engine):
        """确认默认使用 config.WEIGHT_DECAY_LAMBDA"""
        assert memory_engine.config.WEIGHT_DECAY_LAMBDA == 0.1
        w = memory_engine.compute_weight(days=5, access_count=2)
        expected = math.sqrt(3) * math.exp(-0.1 * 5)
        assert w == pytest.approx(expected, rel=1e-6)


# ─── decay_all_weights ────────────────────────────────────────────


class TestDecayAllWeights:
    def test_decay_based_on_real_days(self, memory_engine):
        """基于真实天数衰减，而非简单百分比"""
        chunk_id = memory_engine.store_memory("test decay", "fact")
        # 获取原始权重
        result = memory_engine.collection.get(ids=[chunk_id])
        original_weight = float(result["metadatas"][0]["weight"])

        memory_engine.decay_all_weights()

        result = memory_engine.collection.get(ids=[chunk_id])
        new_weight = float(result["metadatas"][0]["weight"])
        # 新创建的 days=0，weight 应等于 compute_weight(0,0) = 1.0
        assert new_weight == pytest.approx(1.0, abs=0.01)

    def test_decay_older_memory_lower(self, memory_engine):
        """较老的记忆衰减后权重更低"""
        # 手动插入一个"老"记忆
        old_id = memory_engine.store_memory("old memory", "fact")
        meta = memory_engine.collection.get(ids=[old_id])["metadatas"][0]
        meta["created_date"] = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        memory_engine.collection.update(ids=[old_id], metadatas=[meta])

        new_id = memory_engine.store_memory("new memory", "fact")

        memory_engine.decay_all_weights()

        old_meta = memory_engine.collection.get(ids=[old_id])["metadatas"][0]
        new_meta = memory_engine.collection.get(ids=[new_id])["metadatas"][0]
        assert float(old_meta["weight"]) < float(new_meta["weight"])

    def test_decay_empty_collection(self, memory_engine):
        """空集合不报错"""
        memory_engine.decay_all_weights()  # should not raise


# ─── reinforce_memory ─────────────────────────────────────────────


class TestReinforceMemory:
    def test_reinforce_increases_weight(self, memory_engine):
        chunk_id = memory_engine.store_memory("test reinforce", "fact")
        result = memory_engine.collection.get(ids=[chunk_id])
        original_weight = float(result["metadatas"][0]["weight"])

        memory_engine.reinforce_memory(chunk_id, strength=0.3)

        result = memory_engine.collection.get(ids=[chunk_id])
        new_weight = float(result["metadatas"][0]["weight"])
        assert new_weight == pytest.approx(original_weight + 0.3, abs=0.01)

    def test_reinforce_respects_cap(self, memory_engine):
        """权重上限 2.0"""
        chunk_id = memory_engine.store_memory("cap test", "fact")
        # 先设置一个接近上限的权重
        meta = memory_engine.collection.get(ids=[chunk_id])["metadatas"][0]
        meta["weight"] = "1.95"
        memory_engine.collection.update(ids=[chunk_id], metadatas=[meta])

        memory_engine.reinforce_memory(chunk_id, strength=0.2)

        result = memory_engine.collection.get(ids=[chunk_id])
        new_weight = float(result["metadatas"][0]["weight"])
        assert new_weight <= 2.0

    def test_reinforce_updates_last_accessed(self, memory_engine):
        chunk_id = memory_engine.store_memory("access test", "fact")
        today = datetime.now().strftime("%Y-%m-%d")

        memory_engine.reinforce_memory(chunk_id, strength=0.1)

        result = memory_engine.collection.get(ids=[chunk_id])
        assert result["metadatas"][0]["last_accessed"] == today

    def test_reinforce_nonexistent_id(self, memory_engine):
        """不存在的 chunk_id 不报错"""
        memory_engine.reinforce_memory("nonexistent-id", strength=0.1)


# ─── reinforce_path ───────────────────────────────────────────────


class TestReinforcePath:
    def test_reinforce_path_reinforces_all(self, memory_engine):
        ids = []
        for i in range(3):
            cid = memory_engine.store_memory(f"path mem {i}", "fact")
            ids.append(cid)

        memory_engine.reinforce_path(ids, strength=0.2)

        for chunk_id in ids:
            meta = memory_engine.collection.get(ids=[chunk_id])["metadatas"][0]
            weight = float(meta["weight"])
            assert weight >= 1.0 + 0.2 - 0.01  # original ~1.0 + 0.2

    def test_reinforce_path_empty(self, memory_engine):
        """空路径不报错"""
        memory_engine.reinforce_path([], strength=0.1)


# ─── compute_emotion_trend ────────────────────────────────────────


class TestComputeEmotionTrend:
    def test_empty_sessions(self, memory_engine):
        result = memory_engine.compute_emotion_trend([])
        assert result["trend"] == "neutral"

    def test_positive_trend(self, memory_engine):
        sessions = [
            SessionMemory(conversation_id=f"c{i}", emotion_summary="今天很开心")
            for i in range(5)
        ]
        result = memory_engine.compute_emotion_trend(sessions)
        assert result["trend"] == "improving"
        assert len(result["recent_emotions"]) == 5

    def test_negative_trend(self, memory_engine):
        sessions = [
            SessionMemory(conversation_id=f"c{i}", emotion_summary="最近很焦虑")
            for i in range(5)
        ]
        result = memory_engine.compute_emotion_trend(sessions)
        assert result["trend"] == "declining"

    def test_stable_trend(self, memory_engine):
        sessions = [
            SessionMemory(conversation_id="c1", emotion_summary="今天很开心"),
            SessionMemory(conversation_id="c2", emotion_summary="最近很焦虑"),
        ]
        result = memory_engine.compute_emotion_trend(sessions)
        assert result["trend"] == "stable"

    def test_sessions_without_emotion(self, memory_engine):
        sessions = [
            SessionMemory(conversation_id="c1"),  # emotion_summary=""
        ]
        result = memory_engine.compute_emotion_trend(sessions)
        assert result["trend"] == "neutral"

    def test_summary_contains_counts(self, memory_engine):
        sessions = [
            SessionMemory(conversation_id=f"c{i}", emotion_summary="开心")
            for i in range(3)
        ]
        result = memory_engine.compute_emotion_trend(sessions)
        assert "正面3次" in result["summary"]
        assert "负面0次" in result["summary"]


# ─── get_injection_context L1/L2/L3 ──────────────────────────────


class TestGetInjectionContext:
    def _seed_memories(self, engine, count=10):
        for i in range(count):
            engine.store_memory(f"测试记忆内容{i}", "fact")

    def test_level_1_basic(self, memory_engine):
        self._seed_memories(memory_engine)
        state = RelationshipState(current_level=1)
        ctx = memory_engine.get_injection_context("测试", level=1, state=state)
        assert len(ctx["memory_fragments"]) <= 3
        assert "persona_summary" in ctx

    def test_level_1_no_graph(self, memory_engine):
        """L1 不包含图谱相关字段"""
        self._seed_memories(memory_engine)
        state = RelationshipState(current_level=1)
        ctx = memory_engine.get_injection_context("测试", level=1, state=state)
        assert "graph_context" not in ctx
        assert "graph_full" not in ctx

    def test_level_2_with_sessions(self, memory_engine):
        self._seed_memories(memory_engine)
        # 保存一些会话
        for i in range(3):
            memory_engine.save_session(SessionMemory(
                conversation_id=f"conv-{i}",
                topics=["日常"],
                emotion_summary="开心",
            ))
        state = RelationshipState(current_level=2, nickname="小可爱", shared_jokes=["梗1", "梗2"])
        ctx = memory_engine.get_injection_context("测试", level=2, state=state)
        assert len(ctx["memory_fragments"]) <= 8
        assert "relationship_summary" in ctx
        assert "小可爱" in ctx["relationship_summary"]
        assert "emotion_trend" in ctx

    def test_level_2_without_graph_engine(self, memory_engine):
        """无 graph_engine 时 L2 降级不报错"""
        self._seed_memories(memory_engine)
        state = RelationshipState(current_level=2)
        ctx = memory_engine.get_injection_context("测试", level=2, state=state, graph_engine=None)
        assert "graph_context" not in ctx

    def test_level_2_with_mock_graph_engine(self, memory_engine):
        """有 mock graph_engine 时 L2 包含 graph_context"""
        self._seed_memories(memory_engine)
        mock_graph = MagicMock()
        mock_result = MagicMock()
        mock_result.context_summary = "图谱摘要内容"
        mock_graph.search_graph.return_value = mock_result

        state = RelationshipState(current_level=2)
        ctx = memory_engine.get_injection_context("测试", level=2, state=state, graph_engine=mock_graph)
        assert ctx.get("graph_context") == "图谱摘要内容"
        mock_graph.search_graph.assert_called_once_with("测试", max_depth=1, max_nodes=5)

    def test_level_3_evolution_state(self, memory_engine):
        self._seed_memories(memory_engine)
        state = RelationshipState(current_level=3, conflict_mode=True)
        ctx = memory_engine.get_injection_context("测试", level=3, state=state)
        assert "evolution_state" in ctx
        assert ctx["evolution_state"]["conflict_mode"] is True
        assert "attributes" in ctx["evolution_state"]
        assert "de_ai_score" in ctx["evolution_state"]

    def test_level_3_with_mock_graph(self, memory_engine):
        self._seed_memories(memory_engine)
        mock_graph = MagicMock()
        mock_node = MagicMock()
        mock_node.node_id = "node-1"
        mock_node.label = "猫"
        mock_node.node_type = "entity"
        mock_edge = MagicMock()
        mock_edge.source_id = "node-1"
        mock_edge.target_id = "node-2"
        mock_edge.relation = "related_to"
        mock_result = MagicMock()
        mock_result.nodes = [mock_node]
        mock_result.edges = [mock_edge]
        mock_result.context_summary = "完整图谱摘要"
        mock_graph.search_graph.return_value = mock_result

        state = RelationshipState(current_level=3)
        ctx = memory_engine.get_injection_context("测试", level=3, state=state, graph_engine=mock_graph)
        assert "graph_full" in ctx
        assert ctx["graph_full"]["summary"] == "完整图谱摘要"
        assert len(ctx["graph_full"]["nodes"]) == 1
        assert len(ctx["graph_full"]["edges"]) == 1
        # reinforce_path 应该被调用
        mock_graph.reinforce_path.assert_called_once_with(["node-1"])

    def test_level_3_raw_sessions(self, memory_engine):
        self._seed_memories(memory_engine)
        for i in range(3):
            memory_engine.save_session(SessionMemory(
                conversation_id=f"raw-conv-{i}",
                topics=["深度"],
                emotion_summary="满意",
                interaction_type="deep_conversation",
            ))
        state = RelationshipState(current_level=3)
        ctx = memory_engine.get_injection_context("测试", level=3, state=state)
        assert "raw_sessions" in ctx
        assert len(ctx["raw_sessions"]) >= 1

    def test_reinforce_on_hit(self, memory_engine):
        """检索命中时强化记忆"""
        chunk_id = memory_engine.store_memory("强化测试内容", "fact")
        state = RelationshipState(current_level=1)
        ctx = memory_engine.get_injection_context("强化测试", level=1, state=state)

        # 验证权重被强化（原始 1.0 + 0.1 = 1.1）
        meta = memory_engine.collection.get(ids=[chunk_id])["metadatas"][0]
        weight = float(meta["weight"])
        # 如果这条记忆被检索到，权重应该大于1.0
        # 注意：不一定被检索到，但大部分情况下应该可以
        if chunk_id in [f["id"] for f in memory_engine.search_memories("强化测试", n=3, level=1)]:
            assert weight > 1.0

    def test_graph_engine_failure_graceful(self, memory_engine):
        """graph_engine 异常时降级不报错"""
        self._seed_memories(memory_engine)
        mock_graph = MagicMock()
        mock_graph.search_graph.side_effect = RuntimeError("graph error")

        state = RelationshipState(current_level=2)
        ctx = memory_engine.get_injection_context("测试", level=2, state=state, graph_engine=mock_graph)
        # 应该降级，不崩溃
        assert isinstance(ctx, dict)


# ─── estimate_char_count ──────────────────────────────────────────


class TestEstimateCharCount:
    def test_empty_context(self, memory_engine):
        assert memory_engine.estimate_char_count({}) == 0

    def test_string_values(self, memory_engine):
        ctx = {"key1": "hello", "key2": "world"}
        assert memory_engine.estimate_char_count(ctx) == 10

    def test_list_of_strings(self, memory_engine):
        ctx = {"frags": ["abc", "defg"]}
        assert memory_engine.estimate_char_count(ctx) == 7

    def test_list_of_dicts(self, memory_engine):
        ctx = {"items": [{"a": "123"}, {"b": "4567"}]}
        assert memory_engine.estimate_char_count(ctx) == 7

    def test_nested_dict(self, memory_engine):
        ctx = {"meta": {"summary": "hello world"}}
        assert memory_engine.estimate_char_count(ctx) == 11


# ─── trim_to_budget ───────────────────────────────────────────────


class TestTrimToBudget:
    def test_no_trim_needed(self, memory_engine):
        ctx = {"key": "small"}
        result = memory_engine.trim_to_budget(ctx, target_chars=100)
        assert result == ctx

    def test_trim_raw_sessions(self, memory_engine):
        ctx = {
            "raw_sessions": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
            "memory_fragments": ["short"],
        }
        result = memory_engine.trim_to_budget(ctx, target_chars=5)
        assert len(result["raw_sessions"]) <= 1

    def test_trim_removes_graph_full(self, memory_engine):
        ctx = {
            "graph_full": {"nodes": [], "edges": [], "summary": "x" * 200},
            "memory_fragments": ["short"],
        }
        result = memory_engine.trim_to_budget(ctx, target_chars=10)
        assert "graph_full" not in result

    def test_trim_memory_fragments(self, memory_engine):
        ctx = {
            "memory_fragments": ["abcde", "fghij", "klmno"],
        }
        result = memory_engine.trim_to_budget(ctx, target_chars=8)
        assert len(result["memory_fragments"]) < 3
        assert len(result["memory_fragments"]) >= 1

    def test_trim_preserves_at_least_one_fragment(self, memory_engine):
        ctx = {"memory_fragments": ["abcde"]}
        result = memory_engine.trim_to_budget(ctx, target_chars=1)
        # 至少保留一条
        assert len(result["memory_fragments"]) >= 1

    def test_trim_does_not_modify_original(self, memory_engine):
        ctx = {"memory_fragments": ["abcde", "fghij", "klmno"]}
        original_len = len(ctx["memory_fragments"])
        memory_engine.trim_to_budget(ctx, target_chars=5)
        assert len(ctx["memory_fragments"]) == original_len
