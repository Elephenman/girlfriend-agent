# tests/test_api.py
import json
import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.config import Config
from src.core.models import PersonaConfig, PersonalityBase, RelationshipState
from src.engine_server import app, _load_or_init_state, _save_state


@pytest.fixture
def setup_test_env():
    td = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    try:
        config = Config(data_dir=os.path.join(td.name, "gf-agent"))
        config.ensure_dirs()
        _save_state(config, PersonaConfig(), RelationshipState())

        from src.core.git_manager import GitManager
        from src.core.persona import PersonaEngine
        from src.core.memory import MemoryEngine
        from src.core.evolve import EvolveEngine
        from src.core.state_manager import StateManager

        git_mgr = GitManager(data_dir=config.data_dir)
        git_mgr.init_repo()

        state_mgr = StateManager(config)

        app.state.config = config
        app.state.persona = PersonaConfig()
        app.state.relationship = RelationshipState()
        app.state.persona_engine = PersonaEngine(config)
        app.state.memory_engine = MemoryEngine(config)
        app.state.evolve_engine = EvolveEngine(config, git_mgr)
        app.state.git_manager = git_mgr
        app.state.state_manager = state_mgr

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
        persona, relationship = _load_or_init_state(config)
        # persona.json should now exist (self-healed)
        assert os.path.isfile(config.persona_config_path)
        assert isinstance(persona, PersonaConfig)

    def test_relationship_only_missing_self_heals(self, temp_data_dir):
        config = Config(data_dir=temp_data_dir)
        config.ensure_dirs()
        # Create persona.json only
        with open(config.persona_config_path, "w", encoding="utf-8") as f:
            json.dump(PersonaConfig().model_dump(), f)
        persona, relationship = _load_or_init_state(config)
        assert os.path.isfile(config.relationship_config_path)
        assert isinstance(relationship, RelationshipState)

    def test_both_missing_creates_both(self, temp_data_dir):
        config = Config(data_dir=temp_data_dir)
        config.ensure_dirs()
        persona, relationship = _load_or_init_state(config)
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
        persona, relationship = _load_or_init_state(config)
        assert persona.personality_base.warmth == 0.9
        assert relationship.current_level == 2
