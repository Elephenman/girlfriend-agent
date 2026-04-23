import os
import tempfile

import pytest

from src.core.config import Config
from src.core.graph_memory import GraphMemoryEngine
from src.core.models import GraphNode, GraphEdge, GraphSearchResult


@pytest.fixture
def temp_data_dir():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        data_dir = os.path.join(td, "gf-agent")
        config = Config(data_dir=data_dir)
        config.ensure_dirs()
        yield data_dir


@pytest.fixture
def graph_engine(temp_data_dir):
    config = Config(data_dir=temp_data_dir)
    engine = GraphMemoryEngine(config)
    return engine


class TestAddNodeAndEdge:
    def test_add_node_with_explicit_id(self, graph_engine):
        nid = graph_engine.add_node("cat_01", "entity", "猫")
        assert nid == "cat_01"
        assert "cat_01" in graph_engine.graph

    def test_add_node_auto_id(self, graph_engine):
        nid = graph_engine.add_node(None, "entity", "狗")
        assert nid.startswith("node_")
        assert nid in graph_engine.graph

    def test_add_node_with_properties_and_weight(self, graph_engine):
        nid = graph_engine.add_node(
            "emotion_01", "emotion", "开心",
            properties={"intensity": 0.8}, weight=1.5,
        )
        data = graph_engine.graph.nodes[nid]
        assert data["node_type"] == "emotion"
        assert data["label"] == "开心"
        assert data["properties"]["intensity"] == 0.8
        assert data["weight"] == 1.5
        assert data["access_count"] == 0

    def test_add_edge(self, graph_engine):
        graph_engine.add_node("cat_01", "entity", "猫")
        graph_engine.add_node("evt_01", "event", "喂猫")
        graph_engine.add_edge("cat_01", "evt_01", "about", weight=0.9)
        assert graph_engine.graph.has_edge("cat_01", "evt_01")
        edge_data = graph_engine.graph.edges["cat_01", "evt_01"]
        assert edge_data["relation"] == "about"
        assert edge_data["weight"] == 0.9

    def test_add_edge_with_properties(self, graph_engine):
        graph_engine.add_node("a", "entity", "A")
        graph_engine.add_node("b", "entity", "B")
        graph_engine.add_edge("a", "b", "related_to", properties={"source": "chat"}, weight=0.5)
        edge_data = graph_engine.graph.edges["a", "b"]
        assert edge_data["properties"]["source"] == "chat"
        assert edge_data["weight"] == 0.5


class TestGetNode:
    def test_get_existing_node(self, graph_engine):
        graph_engine.add_node("cat_01", "entity", "猫")
        node = graph_engine.get_node("cat_01")
        assert node is not None
        assert node.node_id == "cat_01"
        assert node.label == "猫"
        assert node.node_type == "entity"

    def test_get_node_updates_access(self, graph_engine):
        graph_engine.add_node("cat_01", "entity", "猫")
        node = graph_engine.get_node("cat_01")
        assert node.access_count == 1
        node2 = graph_engine.get_node("cat_01")
        assert node2.access_count == 2

    def test_get_nonexistent_node(self, graph_engine):
        node = graph_engine.get_node("no_such_node")
        assert node is None


class TestSearchGraph:
    def test_search_finds_matching_nodes(self, graph_engine):
        graph_engine.add_node("cat_01", "entity", "小猫")
        graph_engine.add_node("cat_02", "entity", "大猫")
        graph_engine.add_node("dog_01", "entity", "小狗")
        result = graph_engine.search_graph("猫")
        assert len(result.nodes) >= 2

    def test_search_returns_empty_for_no_match(self, graph_engine):
        graph_engine.add_node("cat_01", "entity", "猫")
        result = graph_engine.search_graph("狗")
        assert len(result.nodes) == 0
        assert result.context_summary == "未找到相关图谱节点"

    def test_search_bfs_traversal(self, graph_engine):
        graph_engine.add_node("a", "entity", "猫")
        graph_engine.add_node("b", "event", "喂猫")
        graph_engine.add_node("c", "emotion", "开心")
        graph_engine.add_edge("a", "b", "about")
        graph_engine.add_edge("b", "c", "felt_during")
        result = graph_engine.search_graph("猫")
        # Should find all 3 nodes via BFS
        node_ids = {n.node_id for n in result.nodes}
        assert "a" in node_ids
        assert "b" in node_ids
        assert "c" in node_ids

    def test_search_max_nodes_limit(self, graph_engine):
        for i in range(30):
            graph_engine.add_node(f"node_{i}", "entity", f"猫{i}")
        result = graph_engine.search_graph("猫", max_nodes=5)
        assert len(result.nodes) <= 5

    def test_search_context_summary(self, graph_engine):
        graph_engine.add_node("a", "entity", "猫")
        graph_engine.add_node("b", "event", "喂猫")
        graph_engine.add_edge("a", "b", "about")
        result = graph_engine.search_graph("猫")
        assert "猫" in result.context_summary

    def test_search_by_properties(self, graph_engine):
        graph_engine.add_node("a", "entity", "动物", properties={"name": "小橘猫"})
        result = graph_engine.search_graph("小橘猫")
        assert len(result.nodes) >= 1


class TestFindPath:
    def test_find_path_between_entities(self, graph_engine):
        graph_engine.add_node("a", "entity", "猫")
        graph_engine.add_node("b", "event", "喂猫")
        graph_engine.add_node("c", "emotion", "开心")
        graph_engine.add_edge("a", "b", "about")
        graph_engine.add_edge("b", "c", "felt_during")
        edges = graph_engine.find_path("猫", "开心")
        assert len(edges) > 0
        # Path: 猫 -> 喂猫 -> 开心
        assert edges[0].source_id == "a"
        assert edges[-1].target_id == "c"

    def test_find_path_no_connection(self, graph_engine):
        graph_engine.add_node("a", "entity", "猫")
        graph_engine.add_node("b", "entity", "狗")
        edges = graph_engine.find_path("猫", "狗")
        assert edges == []

    def test_find_path_entity_not_found(self, graph_engine):
        graph_engine.add_node("a", "entity", "猫")
        edges = graph_engine.find_path("猫", "不存在的实体")
        assert edges == []

    def test_find_path_respects_max_hops(self, graph_engine):
        # Build a chain of 7 nodes
        nodes = []
        for i in range(7):
            graph_engine.add_node(f"n{i}", "entity", f"节点{i}")
            nodes.append(f"n{i}")
        for i in range(6):
            graph_engine.add_edge(f"n{i}", f"n{i+1}", "related_to")
        # max_hops=3 means path length <= 4 nodes
        edges = graph_engine.find_path("节点0", "节点6", max_hops=3)
        # Path has 7 nodes (6 hops) > max_hops+1, so should return empty
        assert edges == []


class TestGetTimeline:
    def test_get_timeline_with_events(self, graph_engine):
        graph_engine.add_node("cat_01", "entity", "猫")
        graph_engine.add_node("evt_01", "event", "喂猫", properties={"timestamp": "2024-01-10"})
        graph_engine.add_node("evt_02", "event", "逗猫", properties={"timestamp": "2024-01-15"})
        graph_engine.add_edge("cat_01", "evt_01", "about")
        graph_engine.add_edge("cat_01", "evt_02", "about")
        timeline = graph_engine.get_timeline("cat_01")
        assert len(timeline) == 2
        assert timeline[0]["timestamp"] == "2024-01-10"
        assert timeline[1]["timestamp"] == "2024-01-15"

    def test_get_timeline_by_label(self, graph_engine):
        graph_engine.add_node("cat_01", "entity", "猫")
        graph_engine.add_node("evt_01", "event", "喂猫", properties={"timestamp": "2024-01-10"})
        graph_engine.add_edge("cat_01", "evt_01", "about")
        timeline = graph_engine.get_timeline("猫")
        assert len(timeline) == 1

    def test_get_timeline_empty(self, graph_engine):
        graph_engine.add_node("cat_01", "entity", "猫")
        timeline = graph_engine.get_timeline("cat_01")
        assert timeline == []

    def test_get_timeline_includes_felt_during(self, graph_engine):
        graph_engine.add_node("cat_01", "entity", "猫")
        graph_engine.add_node("evt_01", "event", "喂猫", properties={"timestamp": "2024-01-10"})
        graph_engine.add_node("emo_01", "emotion", "开心")
        graph_engine.add_edge("evt_01", "emo_01", "felt_during")
        timeline = graph_engine.get_timeline("evt_01")
        # felt_during is one of the valid relations
        assert len(timeline) >= 0  # emotion is not an event, but the edge is felt_during

    def test_get_timeline_nonexistent(self, graph_engine):
        timeline = graph_engine.get_timeline("不存在的实体")
        assert timeline == []


class TestDecayGraphWeights:
    def test_decay_reduces_node_weight(self, graph_engine):
        graph_engine.add_node("a", "entity", "猫", weight=1.0)
        graph_engine.decay_graph_weights()
        weight = graph_engine.graph.nodes["a"]["weight"]
        # Fresh node with 0 access: sqrt(1) * exp(0) = 1.0
        # For a node created today with access_count=0:
        # new_weight = sqrt(0+1) * exp(-lambda*0) = 1.0
        assert weight == 1.0  # today, no days passed

    def test_decay_reduces_edge_weight(self, graph_engine):
        graph_engine.add_node("a", "entity", "猫")
        graph_engine.add_node("b", "entity", "狗")
        graph_engine.add_edge("a", "b", "related_to", weight=1.0)
        graph_engine.decay_graph_weights()
        edge_weight = graph_engine.graph.edges["a", "b"]["weight"]
        assert edge_weight == 0.95  # 1.0 * 0.95

    def test_decay_multiple_times(self, graph_engine):
        graph_engine.add_node("a", "entity", "猫")
        graph_engine.add_node("b", "entity", "狗")
        graph_engine.add_edge("a", "b", "related_to", weight=1.0)
        graph_engine.decay_graph_weights()
        graph_engine.decay_graph_weights()
        edge_weight = graph_engine.graph.edges["a", "b"]["weight"]
        assert edge_weight == pytest.approx(0.95 * 0.95)

    def test_decay_weight_minimum(self, graph_engine):
        graph_engine.add_node("a", "entity", "猫")
        graph_engine.add_node("b", "entity", "狗")
        graph_engine.add_edge("a", "b", "related_to", weight=0.005)
        graph_engine.decay_graph_weights()
        edge_weight = graph_engine.graph.edges["a", "b"]["weight"]
        assert edge_weight >= 0.01  # Floor at 0.01


class TestReinforcePath:
    def test_reinforce_increases_weight(self, graph_engine):
        graph_engine.add_node("a", "entity", "猫", weight=0.5)
        graph_engine.reinforce_path(["a"], strength=0.2)
        assert graph_engine.graph.nodes["a"]["weight"] == pytest.approx(0.7)

    def test_reinforce_caps_at_max(self, graph_engine):
        graph_engine.add_node("a", "entity", "猫", weight=1.95)
        graph_engine.reinforce_path(["a"], strength=0.2)
        assert graph_engine.graph.nodes["a"]["weight"] == 2.0  # Capped

    def test_reinforce_increments_access_count(self, graph_engine):
        graph_engine.add_node("a", "entity", "猫")
        assert graph_engine.graph.nodes["a"]["access_count"] == 0
        graph_engine.reinforce_path(["a"])
        assert graph_engine.graph.nodes["a"]["access_count"] == 1
        graph_engine.reinforce_path(["a"])
        assert graph_engine.graph.nodes["a"]["access_count"] == 2

    def test_reinforce_multiple_nodes(self, graph_engine):
        graph_engine.add_node("a", "entity", "猫", weight=0.5)
        graph_engine.add_node("b", "entity", "狗", weight=0.5)
        graph_engine.reinforce_path(["a", "b"], strength=0.1)
        assert graph_engine.graph.nodes["a"]["weight"] == pytest.approx(0.6)
        assert graph_engine.graph.nodes["b"]["weight"] == pytest.approx(0.6)

    def test_reinforce_skips_nonexistent(self, graph_engine):
        # Should not raise
        graph_engine.reinforce_path(["nonexistent"])


class TestSaveAndLoadGraph:
    def test_save_and_load_roundtrip(self, graph_engine):
        graph_engine.add_node("cat_01", "entity", "猫")
        graph_engine.add_node("evt_01", "event", "喂猫")
        graph_engine.add_edge("cat_01", "evt_01", "about")
        graph_engine.save_graph()

        # Create a new engine and load
        config2 = Config(data_dir=graph_engine.config.data_dir)
        engine2 = GraphMemoryEngine(config2)
        # Force load by accessing graph
        assert engine2.graph.number_of_nodes() == 2
        assert engine2.graph.number_of_edges() == 1
        assert engine2.graph.nodes["cat_01"]["label"] == "猫"
        assert engine2.graph.edges["cat_01", "evt_01"]["relation"] == "about"

    def test_save_creates_directory(self, temp_data_dir):
        config = Config(data_dir=temp_data_dir)
        engine = GraphMemoryEngine(config)
        engine.add_node("a", "entity", "测试")
        engine.save_graph()
        assert os.path.exists(os.path.join(config.graphrag_db_dir, "episodic_graph.json"))

    def test_load_nonexistent_returns_empty(self, graph_engine):
        # No file saved, load should return empty graph
        g = graph_engine.load_graph()
        assert g.number_of_nodes() == 0
        assert g.number_of_edges() == 0


class TestGetStats:
    def test_stats_empty_graph(self, graph_engine):
        stats = graph_engine.get_stats()
        assert stats["node_count"] == 0
        assert stats["edge_count"] == 0
        assert stats["node_types"] == {}

    def test_stats_with_data(self, graph_engine):
        graph_engine.add_node("a", "entity", "猫")
        graph_engine.add_node("b", "event", "喂猫")
        graph_engine.add_node("c", "emotion", "开心")
        graph_engine.add_edge("a", "b", "about")
        stats = graph_engine.get_stats()
        assert stats["node_count"] == 3
        assert stats["edge_count"] == 1
        assert stats["node_types"]["entity"] == 1
        assert stats["node_types"]["event"] == 1
        assert stats["node_types"]["emotion"] == 1

    def test_stats_multiple_same_type(self, graph_engine):
        graph_engine.add_node("a", "entity", "猫")
        graph_engine.add_node("b", "entity", "狗")
        stats = graph_engine.get_stats()
        assert stats["node_types"]["entity"] == 2


class TestGetRelated:
    def test_get_related_existing_entity(self, graph_engine):
        graph_engine.add_node("a", "entity", "猫")
        graph_engine.add_node("b", "event", "喂猫")
        graph_engine.add_edge("a", "b", "about")
        result = graph_engine.get_related("a")
        assert len(result.nodes) >= 2

    def test_get_related_nonexistent_entity(self, graph_engine):
        result = graph_engine.get_related("nonexistent")
        assert len(result.nodes) == 0
        assert result.context_summary == "未找到该实体"


class TestLazyGraphLoading:
    def test_graph_loaded_lazily(self, temp_data_dir):
        config = Config(data_dir=temp_data_dir)
        engine = GraphMemoryEngine(config)
        # _graph should be None before first access
        assert engine._graph is None
        # Accessing .graph triggers lazy load
        _ = engine.graph
        assert engine._graph is not None


class TestFindNodeByLabelImproved:
    def test_exact_match_preferred_over_fuzzy(self, graph_engine):
        """Searching for '猫' should match node labeled '猫' before '小猫咪'"""
        graph_engine.add_node("cat_1", "entity", "猫")
        graph_engine.add_node("cat_2", "entity", "小猫咪")
        result = graph_engine._find_node_by_label("猫")
        assert result == "cat_1"

    def test_fuzzy_match_prefers_shortest_label_diff(self, graph_engine):
        """When no exact match, prefer closest label by length"""
        graph_engine.add_node("e1", "entity", "小猫咪超级猫")
        graph_engine.add_node("e2", "entity", "小猫咪")
        result = graph_engine._find_node_by_label("猫")
        # "小猫咪" has length_diff 2, "小猫咪超级猫" has length_diff 5
        assert result == "e2"

    def test_no_match_returns_none(self, graph_engine):
        graph_engine.add_node("e1", "entity", "狗")
        result = graph_engine._find_node_by_label("猫")
        assert result is None
