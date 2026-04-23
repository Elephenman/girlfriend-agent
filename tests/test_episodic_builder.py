import os
import tempfile

import pytest

from src.core.config import Config
from src.core.graph_memory import GraphMemoryEngine
from src.core.episodic_builder import EpisodicBuilder
from src.core.models import SessionMemory


@pytest.fixture
def temp_config():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        data_dir = os.path.join(td, "gf-agent")
        config = Config(data_dir=data_dir)
        config.ensure_dirs()
        yield config


@pytest.fixture
def graph_engine(temp_config):
    return GraphMemoryEngine(temp_config)


@pytest.fixture
def builder(temp_config, graph_engine):
    return EpisodicBuilder(temp_config, graph_engine)


# ---------- add_entity 去重 ----------

def test_add_entity_creates_node(builder, graph_engine):
    node_id = builder.add_entity("猫", entity_type="topic", properties={"color": "white"})
    assert node_id.startswith("ent_")
    node = graph_engine.get_node(node_id)
    assert node is not None
    assert node.label == "猫"
    assert node.node_type == "topic"
    assert node.properties == {"color": "white"}


def test_add_entity_deduplication(builder, graph_engine):
    id1 = builder.add_entity("猫")
    id2 = builder.add_entity("猫")
    assert id1 == id2
    # 图中只有一个节点
    count = sum(1 for _ in graph_engine.graph.nodes(data=True))
    assert count == 1


def test_add_entity_case_insensitive_dedup(builder):
    id1 = builder.add_entity("Python")
    id2 = builder.add_entity("python")
    assert id1 == id2


def test_add_entity_merges_properties(builder, graph_engine):
    id1 = builder.add_entity("猫", properties={"color": "white"})
    id2 = builder.add_entity("猫", properties={"age": "3"})
    assert id1 == id2
    node = graph_engine.get_node(id1)
    assert node.properties == {"color": "white", "age": "3"}


# ---------- add_relation ----------

def test_add_relation_creates_entities(builder, graph_engine):
    success = builder.add_relation("猫", "狗", "hates")
    assert success is True
    # Both entities should be created
    cat_id = builder._find_entity("猫")
    dog_id = builder._find_entity("狗")
    assert cat_id is not None
    assert dog_id is not None
    assert graph_engine.graph.has_edge(cat_id, dog_id)


def test_add_relation_uses_existing_entities(builder, graph_engine):
    cat_id = builder.add_entity("猫")
    dog_id = builder.add_entity("狗")
    builder.add_relation("猫", "狗", "likes")
    # Edge should exist
    assert graph_engine.graph.has_edge(cat_id, dog_id)
    edge_data = graph_engine.graph.edges[cat_id, dog_id]
    assert edge_data["relation"] == "likes"


def test_add_relation_duplicate_increments_weight(builder, graph_engine):
    builder.add_relation("猫", "狗", "likes")
    builder.add_relation("猫", "狗", "likes")
    cat_id = builder._find_entity("猫")
    dog_id = builder._find_entity("狗")
    edge_data = graph_engine.graph.edges[cat_id, dog_id]
    assert edge_data["weight"] == pytest.approx(1.1)


# ---------- add_event ----------

def test_add_event_creates_event_node(builder, graph_engine):
    event_id = builder.add_event(
        event_desc="一起去公园",
        related_entities=["猫", "公园"],
        timestamp="2025-01-15",
        emotion="开心",
    )
    assert event_id.startswith("evt_")
    node = graph_engine.get_node(event_id)
    assert node is not None
    assert node.node_type == "event"
    assert node.label == "一起去公园"
    assert node.properties["timestamp"] == "2025-01-15"
    assert node.properties["emotion"] == "开心"


def test_add_event_links_to_entities(builder, graph_engine):
    event_id = builder.add_event(
        event_desc="一起看电影",
        related_entities=["电影", "周末"],
    )
    # Check edges from entities to event
    movie_id = builder._find_entity("电影")
    weekend_id = builder._find_entity("周末")
    assert graph_engine.graph.has_edge(movie_id, event_id)
    assert graph_engine.graph.has_edge(weekend_id, event_id)
    edge_data = graph_engine.graph.edges[movie_id, event_id]
    assert edge_data["relation"] == "about"


def test_add_event_auto_creates_entities(builder, graph_engine):
    builder.add_event("吃火锅", related_entities=["火锅"])
    # 火锅 entity should be auto-created
    hotpot_id = builder._find_entity("火锅")
    assert hotpot_id is not None
    node = graph_engine.get_node(hotpot_id)
    assert node.label == "火锅"


# ---------- build_causal_chain ----------

def test_build_causal_chain(builder, graph_engine):
    evt1 = builder.add_event("事件A", related_entities=["实体1"])
    evt2 = builder.add_event("事件B", related_entities=["实体2"])
    evt3 = builder.add_event("事件C", related_entities=["实体3"])
    builder.build_causal_chain([evt1, evt2, evt3])
    # Check caused edges
    assert graph_engine.graph.has_edge(evt1, evt2)
    assert graph_engine.graph.has_edge(evt2, evt3)
    assert graph_engine.graph.edges[evt1, evt2]["relation"] == "caused"
    assert graph_engine.graph.edges[evt2, evt3]["relation"] == "caused"


def test_build_causal_chain_skips_missing_nodes(builder, graph_engine):
    evt1 = builder.add_event("事件A", related_entities=[])
    fake_id = "evt_nonexistent"
    evt2 = builder.add_event("事件B", related_entities=[])
    # Should not throw, just skip the missing node edge
    builder.build_causal_chain([evt1, fake_id, evt2])
    # evt1 -> fake_id should NOT exist (fake_id not in graph)
    assert not graph_engine.graph.has_edge(evt1, fake_id)
    # fake_id -> evt2 should NOT exist
    assert not graph_engine.graph.has_edge(fake_id, evt2)


# ---------- merge_entities ----------

def test_merge_entities_transfers_edges(builder, graph_engine):
    a_id = builder.add_entity("实体A")
    b_id = builder.add_entity("实体B")
    c_id = builder.add_entity("实体C")

    # A -> B -> C
    graph_engine.add_edge(a_id, b_id, relation="knows")
    graph_engine.add_edge(b_id, c_id, relation="likes")

    # Merge B into A
    result_id = builder.merge_entities(a_id, b_id)
    assert result_id == a_id

    # B should be removed
    assert not graph_engine.graph.has_node(b_id)
    # A -> C should now exist (migrated from B's out-edge)
    assert graph_engine.graph.has_edge(a_id, c_id)
    # C -> A should NOT exist (was A -> B in-edge, source is A, skip self-loop)
    # But A still has out-edge to C with "likes"
    edge_data = graph_engine.graph.edges[a_id, c_id]
    assert edge_data["relation"] == "likes"


def test_merge_entities_merges_properties(builder, graph_engine):
    a_id = builder.add_entity("实体A", properties={"color": "red"})
    b_id = builder.add_entity("实体B", properties={"size": "big", "color": "blue"})

    builder.merge_entities(a_id, b_id)
    node = graph_engine.get_node(a_id)
    # A's properties override B's
    assert node.properties["color"] == "red"
    assert node.properties["size"] == "big"


def test_merge_entities_updates_cache(builder):
    a_id = builder.add_entity("实体A")
    b_id = builder.add_entity("实体B")
    builder.merge_entities(a_id, b_id)
    # Cache for "实体b" should now point to a_id
    assert builder._entity_cache.get("实体b") == a_id


def test_merge_entities_missing_a(builder, graph_engine):
    b_id = builder.add_entity("实体B")
    result = builder.merge_entities("ent_missing", b_id)
    assert result == b_id  # Return b since a doesn't exist


def test_merge_entities_missing_b(builder, graph_engine):
    a_id = builder.add_entity("实体A")
    result = builder.merge_entities(a_id, "ent_missing")
    assert result == a_id  # Return a since b doesn't exist


# ---------- batch_build ----------

def test_batch_build(builder, graph_engine):
    sessions = [
        SessionMemory(
            conversation_id="conv1",
            topics=["猫", "食物"],
            emotion_summary="开心",
            timestamp="2025-01-10T10:00:00",
        ),
        SessionMemory(
            conversation_id="conv2",
            topics=["旅行"],
            emotion_summary="兴奋",
            timestamp="2025-01-12T14:00:00",
        ),
    ]
    stats = builder.batch_build(sessions)

    # 3 topic entities (entities_added only counts topics in batch_build)
    assert stats["entities_added"] == 3
    assert stats["events_added"] == 2
    # 2 emotion edges + 1 followed_by edge = 3
    assert stats["relations_added"] == 3

    # Check graph has the right structure
    assert graph_engine.graph.number_of_nodes() > 0
    assert graph_engine.graph.number_of_edges() > 0


def test_batch_build_creates_followed_by_chain(builder, graph_engine):
    sessions = [
        SessionMemory(conversation_id="c1", topics=["A"], timestamp="2025-01-01T00:00:00"),
        SessionMemory(conversation_id="c2", topics=["B"], timestamp="2025-01-02T00:00:00"),
        SessionMemory(conversation_id="c3", topics=["C"], timestamp="2025-01-03T00:00:00"),
    ]
    builder.batch_build(sessions)

    # Find all followed_by edges
    followed_edges = [
        (s, t) for s, t, d in graph_engine.graph.edges(data=True)
        if d.get("relation") == "followed_by"
    ]
    assert len(followed_edges) == 2  # c1->c2, c2->c3


def test_batch_build_no_emotion(builder, graph_engine):
    sessions = [
        SessionMemory(conversation_id="c1", topics=["X"], emotion_summary=""),
    ]
    stats = builder.batch_build(sessions)
    assert stats["entities_added"] == 1  # Only the topic entity
    assert stats["relations_added"] == 0  # No emotion, no followed_by


# ---------- get_entity_context ----------

def test_get_entity_context_found(builder, graph_engine):
    cat_id = builder.add_entity("猫", entity_type="topic", properties={"color": "white"})
    event_id = builder.add_event("喂猫", related_entities=["猫"], emotion="开心")

    ctx = builder.get_entity_context("猫")
    assert ctx["found"] is True
    assert ctx["entity"] == "猫"
    assert ctx["type"] == "topic"
    assert ctx["properties"]["color"] == "white"
    assert len(ctx["related_nodes"]) > 0
    assert len(ctx["timeline"]) >= 1


def test_get_entity_context_not_found(builder):
    ctx = builder.get_entity_context("不存在的实体")
    assert ctx["found"] is False
    assert ctx["entity"] == "不存在的实体"


def test_get_entity_context_case_insensitive(builder):
    builder.add_entity("Python", entity_type="topic")
    ctx = builder.get_entity_context("python")
    assert ctx["found"] is True
    assert ctx["entity"] == "Python"


# ---------- integration: save and reload ----------

def test_graph_persistence(temp_config):
    engine1 = GraphMemoryEngine(temp_config)
    builder1 = EpisodicBuilder(temp_config, engine1)

    builder1.add_entity("猫", entity_type="topic")
    builder1.add_event("喂猫", related_entities=["猫"])
    engine1.save_graph()

    # Reload
    engine2 = GraphMemoryEngine(temp_config)
    assert engine2.graph.number_of_nodes() > 0
    found = engine2._find_node_by_label("猫")
    assert found is not None
