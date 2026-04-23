# tests/test_state_manager.py
import json
import os
import pytest

from unittest.mock import Mock

from src.core.config import Config
from src.core.models import PersonaConfig, PersonalityBase, RelationshipState
from src.core.state_manager import StateManager


@pytest.fixture
def temp_data_dir(tmp_path):
    data_dir = str(tmp_path / "test_data")
    return data_dir


@pytest.fixture
def state_mgr(temp_data_dir):
    config = Config(data_dir=temp_data_dir)
    config.ensure_dirs()
    return StateManager(config)


class TestStateManagerSaveLoad:
    def test_save_and_load_persona(self, state_mgr, temp_data_dir):
        persona = PersonaConfig(personality_base=PersonalityBase(warmth=0.9))
        state_mgr.save_persona(persona)
        loaded = state_mgr.load_persona()
        assert loaded.personality_base.warmth == 0.9

    def test_save_and_load_relationship(self, state_mgr, temp_data_dir):
        rel = RelationshipState(current_level=3, intimacy_points=60)
        state_mgr.save_relationship(rel)
        loaded = state_mgr.load_relationship()
        assert loaded.current_level == 3
        assert loaded.intimacy_points == 60

    def test_load_persona_missing_file_returns_default(self, state_mgr):
        loaded = state_mgr.load_persona()
        assert isinstance(loaded, PersonaConfig)
        # Default warmth should be 0.5
        assert loaded.personality_base.warmth == 0.5

    def test_load_relationship_missing_file_returns_default(self, state_mgr):
        loaded = state_mgr.load_relationship()
        assert isinstance(loaded, RelationshipState)
        assert loaded.current_level == 0

    def test_load_persona_corrupt_json_raises(self, state_mgr, temp_data_dir):
        config = Config(data_dir=temp_data_dir)
        with open(config.persona_config_path, "w") as f:
            f.write("{invalid json")
        # load_persona should raise when json is corrupt
        with pytest.raises(Exception):
            state_mgr.load_persona()


class TestStateManagerLoadOrInit:
    def test_load_or_init_persona_creates_default_when_missing(self, temp_data_dir):
        config = Config(data_dir=temp_data_dir)
        config.ensure_dirs()
        sm = StateManager(config)
        persona = sm.load_or_init_persona()
        assert isinstance(persona, PersonaConfig)
        assert os.path.isfile(config.persona_config_path)

    def test_load_or_init_persona_preserves_existing(self, temp_data_dir):
        config = Config(data_dir=temp_data_dir)
        config.ensure_dirs()
        custom = PersonaConfig(personality_base=PersonalityBase(warmth=0.9))
        sm = StateManager(config)
        sm.save_persona(custom)
        loaded = sm.load_or_init_persona()
        assert loaded.personality_base.warmth == 0.9

    def test_load_or_init_relationship_creates_default_when_missing(self, temp_data_dir):
        config = Config(data_dir=temp_data_dir)
        config.ensure_dirs()
        sm = StateManager(config)
        rel = sm.load_or_init_relationship()
        assert isinstance(rel, RelationshipState)
        assert os.path.isfile(config.relationship_config_path)

    def test_load_or_init_relationship_preserves_existing(self, temp_data_dir):
        config = Config(data_dir=temp_data_dir)
        config.ensure_dirs()
        custom = RelationshipState(current_level=3, intimacy_points=60)
        sm = StateManager(config)
        sm.save_relationship(custom)
        loaded = sm.load_or_init_relationship()
        assert loaded.current_level == 3


class TestStateManagerReloadAll:
    def test_reload_all_syncs_app_state(self, state_mgr, temp_data_dir):
        app = Mock()
        app.state = Mock()

        custom_persona = PersonaConfig(personality_base=PersonalityBase(warmth=0.8))
        custom_rel = RelationshipState(current_level=4)
        state_mgr.save_persona(custom_persona)
        state_mgr.save_relationship(custom_rel)

        state_mgr.reload_all(app)
        assert app.state.persona.personality_base.warmth == 0.8
        assert app.state.relationship.current_level == 4


class TestStateManagerPersistRelationship:
    def test_persist_relationship_writes_current_state(self, state_mgr, temp_data_dir):
        app = Mock()
        app.state = Mock()
        app.state.relationship = RelationshipState(current_level=5, intimacy_points=100)

        state_mgr.persist_relationship(app)

        loaded = state_mgr.load_relationship()
        assert loaded.current_level == 5
        assert loaded.intimacy_points == 100