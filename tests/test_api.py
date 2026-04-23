# tests/test_api.py
import asyncio
import json
import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.config import Config
from src.core.models import PersonaConfig, PersonalityBase, RelationshipState
from src.core.state_manager import StateManager
from src.engine_server import app


@pytest.fixture
def setup_test_env():
    td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    try:
        config = Config(data_dir=os.path.join(td.name, "gf-agent"))
        config.ensure_dirs()

        from src.core.git_manager import GitManager
        from src.core.persona import PersonaEngine
        from src.core.memory import MemoryEngine
        from src.core.evolve import EvolveEngine
        from src.core.graph_memory import GraphMemoryEngine
        from src.core.episodic_builder import EpisodicBuilder

        git_mgr = GitManager(data_dir=config.data_dir)
        git_mgr.init_repo()

        state_mgr = StateManager(config)
        # Use load_or_init to self-heal and persist defaults
        persona = state_mgr.load_or_init_persona()
        relationship = state_mgr.load_or_init_relationship()

        graph_engine = GraphMemoryEngine(config)
        episodic_builder = EpisodicBuilder(config, graph_engine)

        app.state.config = config
        app.state.persona = persona
        app.state.relationship = relationship
        app.state.persona_engine = PersonaEngine(config)
        app.state.memory_engine = MemoryEngine(config)
        app.state.evolve_engine = EvolveEngine(config, git_mgr)
        app.state.git_manager = git_mgr
        app.state.state_manager = state_mgr
        app.state.state_lock = asyncio.Lock()
        app.state.graph_engine = graph_engine
        app.state.episodic_builder = episodic_builder

        yield config
    finally:
        td.cleanup()


@pytest.mark.anyio
async def test_health_endpoint(setup_test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


@pytest.mark.anyio
async def test_status_endpoint(setup_test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "current_level" in data
        assert "intimacy_points" in data


@pytest.mark.anyio
async def test_chat_endpoint(setup_test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/chat", json={
            "user_message": "你好",
            "level": 1,
            "interaction_type": "daily_chat",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "persona_prompt" in data
        assert "memory_fragments" in data
        assert "relationship_summary" in data
        assert "de_ai_instructions" in data


@pytest.mark.anyio
async def test_memory_update_and_search(setup_test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/memory/update", json={
            "content": "用户喜欢猫",
            "memory_type": "fact",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        resp = await client.post("/memory/search", json={
            "query": "猫",
            "level": 1,
        })
        assert resp.status_code == 200


@pytest.mark.anyio
async def test_persona_get(setup_test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/persona")
        assert resp.status_code == 200


@pytest.mark.anyio
async def test_persona_apply_template(setup_test_env):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/persona/apply-template", json={
            "template_id": "default",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


class TestLoadOrInitStateSelfHeal:
    def test_persona_only_missing_self_heals(self, temp_data_dir):
        config = Config(data_dir=temp_data_dir)
        config.ensure_dirs()
        # Create relationship.json only
        with open(config.relationship_config_path, "w", encoding="utf-8") as f:
            json.dump(RelationshipState().model_dump(), f)
        sm = StateManager(config)
        persona = sm.load_or_init_persona()
        # persona.json should now exist (self-healed)
        assert os.path.isfile(config.persona_config_path)
        assert isinstance(persona, PersonaConfig)

    def test_relationship_only_missing_self_heals(self, temp_data_dir):
        config = Config(data_dir=temp_data_dir)
        config.ensure_dirs()
        # Create persona.json only
        with open(config.persona_config_path, "w", encoding="utf-8") as f:
            json.dump(PersonaConfig().model_dump(), f)
        sm = StateManager(config)
        relationship = sm.load_or_init_relationship()
        assert os.path.isfile(config.relationship_config_path)
        assert isinstance(relationship, RelationshipState)

    def test_both_missing_creates_both(self, temp_data_dir):
        config = Config(data_dir=temp_data_dir)
        config.ensure_dirs()
        sm = StateManager(config)
        persona = sm.load_or_init_persona()
        relationship = sm.load_or_init_relationship()
        assert os.path.isfile(config.persona_config_path)
        assert os.path.isfile(config.relationship_config_path)

    def test_both_exist_no_overwrite(self, temp_data_dir):
        config = Config(data_dir=temp_data_dir)
        config.ensure_dirs()
        # Create both with non-default data
        custom_persona = PersonaConfig(personality_base=PersonalityBase(warmth=0.9))
        with open(config.persona_config_path, "w", encoding="utf-8") as f:
            json.dump(custom_persona.model_dump(), f)
        custom_rel = RelationshipState(current_level=2, intimacy_points=30)
        with open(config.relationship_config_path, "w", encoding="utf-8") as f:
            json.dump(custom_rel.model_dump(), f)
        sm = StateManager(config)
        persona = sm.load_or_init_persona()
        relationship = sm.load_or_init_relationship()
        assert persona.personality_base.warmth == 0.9
        assert relationship.current_level == 2


class TestChatService:
    def test_mutate_state_updates_intimacy(self, setup_test_env):
        """Verify intimacy is updated according to interaction type"""
        from src.core.chat_service import ChatService
        from src.core.models import ChatRequest

        req = ChatRequest(user_message="hello", interaction_type="daily_chat", level=1)
        initial_rel = RelationshipState()
        app_state = app.state
        chat_service = ChatService(
            persona_engine=app_state.persona_engine,
            memory_engine=app_state.memory_engine,
            evolve_engine=app_state.evolve_engine,
            graph_engine=app_state.graph_engine,
        )
        result = chat_service.mutate_state(req, app_state.persona, initial_rel)
        # intimacy_points should increase by 1 (daily_chat gain)
        assert result.intimacy_points > initial_rel.intimacy_points

    def test_build_context_returns_expected_keys(self, setup_test_env):
        """Verify result dict contains all expected keys"""
        from src.core.chat_service import ChatService
        from src.core.models import ChatRequest

        req = ChatRequest(user_message="hello", level=1)
        app_state = app.state
        chat_service = ChatService(
            persona_engine=app_state.persona_engine,
            memory_engine=app_state.memory_engine,
            evolve_engine=app_state.evolve_engine,
            graph_engine=app_state.graph_engine,
        )
        ctx = chat_service.build_context(req, app_state.persona, RelationshipState())
        assert "full_prompt" in ctx
        assert "rel_summary" in ctx
        assert "memory_ctx" in ctx
        assert "de_ai_instructions" in ctx


class TestGraphRouterPydanticValidation:
    @pytest.mark.anyio
    async def test_add_entity_empty_name_rejected(self, setup_test_env):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/graph/add-entity", json={"entity_name": ""})
            assert r.status_code == 422

    @pytest.mark.anyio
    async def test_add_entity_invalid_type_rejected(self, setup_test_env):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/graph/add-entity", json={"entity_name": "test", "entity_type": "invalid"})
            assert r.status_code == 422

    @pytest.mark.anyio
    async def test_add_relation_empty_source_rejected(self, setup_test_env):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/graph/add-relation", json={"source_entity": "", "target_entity": "ok"})
            assert r.status_code == 422

    @pytest.mark.anyio
    async def test_add_relation_invalid_type_rejected(self, setup_test_env):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/graph/add-relation", json={
                "source_entity": "a", "target_entity": "b", "relation_type": "invalid"
            })
            assert r.status_code == 422

    @pytest.mark.anyio
    async def test_search_empty_query_rejected(self, setup_test_env):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/graph/search", json={"query": ""})
            assert r.status_code == 422

    @pytest.mark.anyio
    async def test_search_excessive_max_nodes_rejected(self, setup_test_env):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/graph/search", json={"query": "test", "max_nodes": 200})
            assert r.status_code == 422

    @pytest.mark.anyio
    async def test_reinforce_empty_chunk_id_rejected(self, setup_test_env):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/memory/reinforce", json={"chunk_id": ""})
            assert r.status_code == 422

    @pytest.mark.anyio
    async def test_emotion_trend_invalid_count_rejected(self, setup_test_env):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/memory/emotion-trend", json={"count": 0})
            assert r.status_code == 422


class TestGraphChatIntegration:
    """Integration test: verify graph_context is injected into ChatService.build_context at Level 2+"""

    @pytest.mark.anyio
    async def test_graph_context_injected_at_level_2(self, setup_test_env):
        """Add graph entities via API, then verify /chat at level 2 includes graph_context in memory_ctx"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Add an entity to the graph
            r = await client.post("/graph/add-entity", json={
                "entity_name": "小猫咪",
                "entity_type": "entity",
                "properties": {"type": "pet"},
            })
            assert r.status_code == 200

            # Add a relation
            r = await client.post("/graph/add-relation", json={
                "source_entity": "小猫咪",
                "target_entity": "喂食",
                "relation_type": "caused",
            })
            assert r.status_code == 200

            # Call /chat at level 2 - should include graph_context
            r = await client.post("/chat", json={
                "user_message": "小猫咪",
                "level": 2,
                "interaction_type": "daily_chat",
            })
            assert r.status_code == 200

    def test_build_context_with_graph_engine_includes_graph_context(self, setup_test_env):
        """Unit-level integration: ChatService.build_context at level 2 injects graph_context"""
        from src.core.chat_service import ChatService, ChatContext
        from src.core.models import ChatRequest

        req = ChatRequest(user_message="小猫咪", level=2)
        app_state = app.state

        # Ensure graph has data for search
        graph_engine = app_state.graph_engine
        graph_engine.add_node("cat_01", "entity", "小猫咪", properties={"type": "pet"})
        graph_engine.add_node("act_01", "event", "喂食")
        graph_engine.add_edge("cat_01", "act_01", "caused")

        chat_service = ChatService(
            persona_engine=app_state.persona_engine,
            memory_engine=app_state.memory_engine,
            evolve_engine=app_state.evolve_engine,
            graph_engine=app_state.graph_engine,
        )

        ctx: ChatContext = chat_service.build_context(req, app_state.persona, RelationshipState())
        assert "memory_ctx" in ctx
        memory_ctx = ctx["memory_ctx"]
        # Level 2 should inject graph_context if graph data is available
        assert "graph_context" in memory_ctx
        # graph_context should mention the entity we added
        assert "小猫咪" in memory_ctx["graph_context"]

    def test_build_context_without_graph_engine_no_graph_context(self, setup_test_env):
        """Unit-level integration: ChatService.build_context at level 2 without graph_engine has no graph_context"""
        from src.core.chat_service import ChatService, ChatContext
        from src.core.models import ChatRequest

        req = ChatRequest(user_message="test", level=2)
        app_state = app.state

        chat_service = ChatService(
            persona_engine=app_state.persona_engine,
            memory_engine=app_state.memory_engine,
            evolve_engine=app_state.evolve_engine,
            graph_engine=None,  # No graph engine
        )

        ctx: ChatContext = chat_service.build_context(req, app_state.persona, RelationshipState())
        memory_ctx = ctx["memory_ctx"]
        # Without graph engine, graph_context should not be present (or be empty)
        graph_ctx = memory_ctx.get("graph_context", "")
        assert graph_ctx == ""


class TestGraphRouterIdempotency:
    """Verify add-entity/add-relation endpoints are idempotent"""

    @pytest.mark.anyio
    async def test_add_entity_idempotent_returns_existing(self, setup_test_env):
        """Adding the same entity twice should return the same node_id, not create duplicate"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r1 = await client.post("/graph/add-entity", json={
                "entity_name": "猫咪",
                "entity_type": "entity",
            })
            assert r1.status_code == 200
            data1 = r1.json()
            assert data1["created"] is True

            r2 = await client.post("/graph/add-entity", json={
                "entity_name": "猫咪",
                "entity_type": "entity",
                "properties": {"color": "orange"},
            })
            assert r2.status_code == 200
            data2 = r2.json()
            assert data2["node_id"] == data1["node_id"]
            assert data2["created"] is False

    @pytest.mark.anyio
    async def test_add_relation_idempotent_strengthens_weight(self, setup_test_env):
        """Adding same relation twice should strengthen weight, not create duplicate edge"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # First add entities
            await client.post("/graph/add-entity", json={"entity_name": "猫"})
            await client.post("/graph/add-entity", json={"entity_name": "鱼"})

            r1 = await client.post("/graph/add-relation", json={
                "source_entity": "猫",
                "target_entity": "鱼",
                "relation_type": "caused",
            })
            assert r1.status_code == 200

            r2 = await client.post("/graph/add-relation", json={
                "source_entity": "猫",
                "target_entity": "鱼",
                "relation_type": "caused",
            })
            assert r2.status_code == 200

            # Verify no duplicate edges
            graph_engine = app.state.graph_engine
            source_id = app.state.episodic_builder._find_entity("猫")
            target_id = app.state.episodic_builder._find_entity("鱼")
            # Should have exactly one edge between these nodes with the same relation
            edge_count = 0
            for u, v, d in graph_engine.graph.edges(data=True):
                if u == source_id and v == target_id and d.get("relation") == "caused":
                    edge_count += 1
            assert edge_count == 1
