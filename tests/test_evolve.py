import json
import os

import pytest

from src.core.config import Config
from src.core.evolve import EvolveEngine
from src.core.models import RelationshipState, AttributePoints, DeAiDimensions
from src.core.git_manager import GitManager


@pytest.fixture
def evolve_engine(temp_data_dir):
    config = Config(data_dir=temp_data_dir)
    config.ensure_dirs()
    git_mgr = GitManager(data_dir=temp_data_dir)
    git_mgr.init_repo()
    engine = EvolveEngine(config, git_mgr)
    return engine


class TestEvolveIntimacy:
    def test_daily_chat_adds_1(self, evolve_engine):
        state = RelationshipState()
        result = evolve_engine.update_intimacy("daily_chat", state)
        assert result.intimacy_points == 1

    def test_deep_conversation_adds_3(self, evolve_engine):
        state = RelationshipState()
        result = evolve_engine.update_intimacy("deep_conversation", state)
        assert result.intimacy_points == 3

    def test_invalid_type_no_change(self, evolve_engine):
        state = RelationshipState()
        result = evolve_engine.update_intimacy("invalid_type", state)
        assert result.intimacy_points == 0


class TestEvolveAttributes:
    def test_daily_chat_adds_attributes(self, evolve_engine):
        state = RelationshipState()
        result = evolve_engine.add_interaction_attributes("daily_chat", state)
        assert result.attributes.care > 0

    def test_deep_conversation_adds_specific(self, evolve_engine):
        state = RelationshipState()
        result = evolve_engine.add_interaction_attributes("deep_conversation", state)
        assert result.attributes.care >= 1
        assert result.attributes.understanding >= 1
        assert result.attributes.sensitivity >= 1

    def test_attributes_clamp_at_100(self, evolve_engine):
        state = RelationshipState(attributes=AttributePoints(care=100))
        result = evolve_engine.add_interaction_attributes("deep_conversation", state)
        assert result.attributes.care == 100


class TestEvolveLevelUp:
    def test_check_level_up_threshold(self, evolve_engine):
        state = RelationshipState(intimacy_points=15, current_level=0)
        can_level = evolve_engine.check_level_up(state)
        assert can_level is True  # 15 >= threshold for level 1 (10)

    def test_no_level_up_below_threshold(self, evolve_engine):
        state = RelationshipState(intimacy_points=5, current_level=0)
        can_level = evolve_engine.check_level_up(state)
        assert can_level is False

    def test_process_level_up_gives_bonus_points(self, evolve_engine):
        state = RelationshipState(intimacy_points=15, current_level=0)
        result = evolve_engine.process_level_up(1, state)
        assert result.current_level == 1

    def test_max_level_no_level_up(self, evolve_engine):
        state = RelationshipState(intimacy_points=9999, current_level=6)
        can_level = evolve_engine.check_level_up(state)
        assert can_level is False


class TestEvolveDeAi:
    def test_de_ai_score_updates_with_level(self, evolve_engine):
        state = RelationshipState(current_level=3)
        result = evolve_engine.update_de_ai_score(state)
        # Higher level → lower structured_output, higher emotion_naturalness
        assert result.de_ai_score.structured_output < 0.8  # default is 0.8
        assert result.de_ai_score.emotion_naturalness > 0.3  # default is 0.3

    def test_de_ai_behavior_rules(self, evolve_engine):
        de_ai = DeAiDimensions(structured_output=0.2, emotion_naturalness=0.8)
        rules = evolve_engine.get_de_ai_behavior_rules(de_ai)
        assert isinstance(rules, list)
        assert len(rules) > 0


class TestEvolveCycle:
    def test_evolution_cycle_creates_log(self, evolve_engine):
        state = RelationshipState()
        from src.core.models import SessionMemory
        sessions = [
            SessionMemory(conversation_id=f"conv-{i}", topics=["test"], interaction_type="daily_chat")
            for i in range(7)
        ]
        result_state, log_entry = evolve_engine.run_evolution_cycle(sessions, state)
        assert log_entry is not None
        assert log_entry.trigger == "7次对话"

    def test_evolution_adjustment_within_10pct(self, evolve_engine):
        state = RelationshipState(
            attributes=AttributePoints(care=50),
        )
        from src.core.models import PersonaConfig, PersonalityBase
        persona = PersonaConfig(personality_base=PersonalityBase(warmth=0.5))
        adjustments = evolve_engine.calculate_evolution_adjustments(persona, state)
        for dim, delta in adjustments.items():
            if delta != 0:
                assert abs(delta) <= 0.1, f"Dimension {dim} changed by {delta}, exceeds 10%"


class TestConflictTrigger:
    def test_conflict_after_5_gap(self, evolve_engine):
        state = RelationshipState(conflict_mode=False)
        result = evolve_engine.check_conflict_trigger(5, state)
        assert result.conflict_mode is True

    def test_no_conflict_under_5(self, evolve_engine):
        state = RelationshipState(conflict_mode=False)
        result = evolve_engine.check_conflict_trigger(3, state)
        assert result.conflict_mode is False


class TestEvolutionDirection:
    def test_calculate_direction(self, evolve_engine):
        state = RelationshipState(
            attributes=AttributePoints(care=100, sensitivity=80),
        )
        direction = evolve_engine.calculate_evolution_direction(state)
        assert "primary" in direction
        assert "secondary" in direction
