import json
import os
import shutil

import pytest

from src.core.config import Config
from src.core.models import PersonaConfig, PersonalityBase, RelationshipState, AttributePoints, DeAiDimensions
from src.core.persona import PersonaEngine, ATTR_TO_PERSONALITY_MAP


@pytest.fixture
def persona_engine(temp_data_dir):
    config = Config(data_dir=temp_data_dir)
    config.ensure_dirs()
    engine = PersonaEngine(config)
    return engine


@pytest.fixture
def persona_engine_with_prompts(persona_engine, temp_data_dir):
    # Copy prompts to config level_prompts dir
    src_prompts = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "prompts")
    dst_prompts = os.path.join(temp_data_dir, "config", "level_prompts")
    os.makedirs(dst_prompts, exist_ok=True)
    if os.path.isdir(src_prompts):
        for f in os.listdir(src_prompts):
            shutil.copy2(os.path.join(src_prompts, f), dst_prompts)
    return persona_engine


class TestAttrToPersonalityMap:
    def test_all_8_attributes_mapped(self):
        expected_attrs = {"care", "understanding", "expression", "memory_attr",
                          "humor", "intuition", "courage", "sensitivity"}
        assert set(ATTR_TO_PERSONALITY_MAP.keys()) == expected_attrs

    def test_mapping_targets_valid_dims(self):
        valid_dims = {"warmth", "humor", "proactivity", "gentleness",
                      "stubbornness", "curiosity", "shyness"}
        for attr, mappings in ATTR_TO_PERSONALITY_MAP.items():
            for dim, weight in mappings.items():
                assert dim in valid_dims, f"{attr} maps to invalid dim {dim}"
                assert -1.0 <= weight <= 1.0


class TestPersonaEngineLoad:
    def test_load_persona_from_config(self, persona_engine, temp_data_dir):
        persona_data = PersonaConfig(
            personality_base=PersonalityBase(warmth=0.9),
            speech_style={"greeting": "嗨~"},
        ).model_dump()
        with open(os.path.join(temp_data_dir, "config", "persona.json"), "w") as f:
            json.dump(persona_data, f)

        result = persona_engine.load_persona()
        assert result.personality_base.warmth == 0.9
        assert result.speech_style.greeting == "嗨~"

    def test_load_persona_missing_file_returns_default(self, persona_engine):
        result = persona_engine.load_persona()
        assert result.personality_base.warmth == 0.5


class TestPersonaEngineApplyTemplate:
    def test_apply_template_copies_to_config(self, persona_engine, temp_data_dir):
        persona_engine.apply_template("default")
        config_path = os.path.join(temp_data_dir, "config", "persona.json")
        assert os.path.isfile(config_path)
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["name"] == "默认"

    def test_apply_template_unknown_raises(self, persona_engine):
        with pytest.raises(FileNotFoundError):
            persona_engine.apply_template("nonexistent")


class TestPersonaEngineGetCurrentPersona:
    def test_base_persona_no_attributes(self, persona_engine):
        persona = PersonaConfig(personality_base=PersonalityBase(warmth=0.5))
        state = RelationshipState()
        result = persona_engine.get_current_persona(persona, state)
        assert result.warmth == 0.5

    def test_attribute_influences_persona(self, persona_engine):
        persona = PersonaConfig(personality_base=PersonalityBase(warmth=0.5, humor=0.3))
        state = RelationshipState(
            attributes=AttributePoints(care=100, humor=50),
        )
        result = persona_engine.get_current_persona(persona, state)
        # care -> warmth+0.8, care=100 → warmth = 0.5 + 100*0.8/100 = 0.5+0.8 = 1.3 → clamped to 1.0
        assert result.warmth == 1.0
        # humor -> humor+1.0, humor=50 → humor = 0.3 + 50*1.0/100 = 0.3+0.5 = 0.8
        assert result.humor == 0.8


class TestPersonaEngineGetLevelPrompt:
    def test_get_level_0_prompt(self, persona_engine_with_prompts, temp_data_dir):
        state = RelationshipState()
        result = persona_engine_with_prompts.get_level_prompt(0, state)
        # Check for Chinese characters in the prompt ("初次相遇" means "first meeting")
        assert "初次" in result or "level" in result.lower() or "陌生" in result or "克制" in result

    def test_prompt_variable_substitution(self, persona_engine_with_prompts, temp_data_dir):
        state = RelationshipState(nickname="小宝", shared_jokes=["猫梗"], rituals=["晚安吻"])
        result = persona_engine_with_prompts.get_level_prompt(3, state)
        # Should not contain raw placeholders
        assert "{nickname}" not in result
        assert "{shared_jokes}" not in result


class TestPersonaEngineGetDeAiInstructions:
    def test_high_structured_output(self, persona_engine):
        de_ai = DeAiDimensions(structured_output=0.9, precision_level=0.8)
        state = RelationshipState(de_ai_score=de_ai)
        instructions = persona_engine.get_de_ai_instructions(state)
        assert "结构化" in instructions or "减少" in instructions or "避免" in instructions

    def test_low_structured_output(self, persona_engine):
        de_ai = DeAiDimensions(structured_output=0.2, precision_level=0.2)
        state = RelationshipState(de_ai_score=de_ai)
        instructions = persona_engine.get_de_ai_instructions(state)
        assert isinstance(instructions, str)


class TestPersonaEngineUpdateField:
    def test_update_single_field(self, persona_engine, temp_data_dir):
        persona_engine.apply_template("default")
        persona_engine.update_persona_field("likes", ["新爱好"])
        result = persona_engine.load_persona()
        assert "新爱好" in result.likes

    def test_update_nested_field(self, persona_engine, temp_data_dir):
        persona_engine.apply_template("default")
        persona_engine.update_persona_field("personality_base.warmth", 0.9)
        result = persona_engine.load_persona()
        assert result.personality_base.warmth == 0.9


class TestUpdatePersonaFieldPreValidate:
    def test_invalid_value_does_not_mutate_persona_object(self, temp_data_dir):
        """Verify that a type-mismatch value doesn't leave persona in illegal state"""
        config = Config(data_dir=temp_data_dir)
        config.ensure_dirs()
        from src.core.state_manager import StateManager
        state_mgr = StateManager(config)
        state_mgr.save_persona(PersonaConfig())
        persona_engine = PersonaEngine(config)

        with pytest.raises(Exception):
            persona_engine.update_persona_field("personality_base.warmth", "not_a_float")

        # persona.json should still contain original valid value
        loaded = persona_engine.load_persona()
        assert isinstance(loaded.personality_base.warmth, float)

    def test_valid_value_with_type_coercion(self, temp_data_dir):
        """Verify that int->float coercion works correctly via pre-validation"""
        config = Config(data_dir=temp_data_dir)
        config.ensure_dirs()
        from src.core.state_manager import StateManager
        state_mgr = StateManager(config)
        state_mgr.save_persona(PersonaConfig())
        persona_engine = PersonaEngine(config)

        # warmth is float field, passing int 1 should be coerced to 1.0
        result = persona_engine.update_persona_field("personality_base.warmth", 1)
        assert result.personality_base.warmth == 1.0  # coerced to float
