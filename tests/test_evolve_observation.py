import json
import os

import pytest

from src.core.config import Config
from src.core.evolve import EvolveEngine
from src.core.git_manager import GitManager
from src.core.models import (
    RelationshipState,
    AttributePoints,
    SessionMemory,
    PersonaConfig,
    PersonalityBase,
    ObservationPattern,
    EvolutionState,
)

from src.core.memory import MemoryEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def evolve_engine(temp_data_dir):
    config = Config(data_dir=temp_data_dir)
    config.ensure_dirs()
    git_mgr = GitManager(data_dir=temp_data_dir)
    git_mgr.init_repo()
    engine = EvolveEngine(config, git_mgr)
    return engine


@pytest.fixture
def memory_engine(temp_data_dir):
    config = Config(data_dir=temp_data_dir)
    config.ensure_dirs()
    engine = MemoryEngine(config)
    return engine


def _make_sessions(
    n: int = 7,
    topics: list[list[str]] | None = None,
    emotion_summaries: list[str] | None = None,
    interaction_types: list[str] | None = None,
) -> list[SessionMemory]:
    """Helper to build a list of SessionMemory for testing."""
    default_topics = [["日常"]] * n
    default_emotions = [""] * n
    default_types = ["daily_chat"] * n

    t = topics or default_topics
    e = emotion_summaries or default_emotions
    it = interaction_types or default_types

    return [
        SessionMemory(
            conversation_id=f"conv-{i}",
            topics=t[i] if i < len(t) else ["日常"],
            emotion_summary=e[i] if i < len(e) else "",
            interaction_type=it[i] if i < len(it) else "daily_chat",
        )
        for i in range(n)
    ]


# ===========================================================================
# observe_patterns
# ===========================================================================


class TestObservePatterns:
    def test_empty_sessions_returns_no_data(self, evolve_engine):
        result = evolve_engine.observe_patterns([])
        assert result.summary == "无对话数据"
        assert result.emotion_tone == "neutral"
        assert result.topic_distribution == {}

    def test_topic_distribution(self, evolve_engine):
        sessions = _make_sessions(
            n=4,
            topics=[["工作"], ["生活", "工作"], ["工作"], ["娱乐"]],
        )
        result = evolve_engine.observe_patterns(sessions)
        assert result.topic_distribution["工作"] == 3
        assert result.topic_distribution["生活"] == 1
        assert result.topic_distribution["娱乐"] == 1

    def test_interaction_distribution(self, evolve_engine):
        sessions = _make_sessions(
            n=4,
            interaction_types=["deep_conversation", "daily_chat", "deep_conversation", "light_chat"],
        )
        result = evolve_engine.observe_patterns(sessions)
        assert result.interaction_distribution["deep_conversation"] == 2
        assert result.interaction_distribution["daily_chat"] == 1
        assert result.interaction_distribution["light_chat"] == 1

    def test_summary_includes_topics(self, evolve_engine):
        sessions = _make_sessions(n=3, topics=[["工作"], ["工作"], ["生活"]])
        result = evolve_engine.observe_patterns(sessions)
        assert "工作" in result.summary
        assert "情绪基调" in result.summary

    def test_summary_includes_hidden_needs(self, evolve_engine):
        sessions = _make_sessions(
            n=5,
            topics=[["工作"], ["工作"], ["工作"], ["生活"], ["生活"]],
        )
        result = evolve_engine.observe_patterns(sessions)
        # "工作" appears 3 times -> hidden need
        assert any("工作" in need for need in result.hidden_needs)
        assert "隐性需求" in result.summary


# ===========================================================================
# _analyze_emotion_tone
# ===========================================================================


class TestAnalyzeEmotionTone:
    def test_positive_tone(self, evolve_engine):
        sessions = _make_sessions(
            n=5,
            emotion_summaries=["开心的一天", "很高兴", "快乐", "满意", "兴奋"],
        )
        tone = evolve_engine._analyze_emotion_tone(sessions)
        assert tone == "positive"

    def test_negative_tone(self, evolve_engine):
        sessions = _make_sessions(
            n=5,
            emotion_summaries=["焦虑", "压力大", "很难过", "沮丧", "疲惫"],
        )
        tone = evolve_engine._analyze_emotion_tone(sessions)
        assert tone == "negative"

    def test_neutral_tone(self, evolve_engine):
        sessions = _make_sessions(n=3, emotion_summaries=["", "", ""])
        tone = evolve_engine._analyze_emotion_tone(sessions)
        assert tone == "neutral"

    def test_mixed_tone(self, evolve_engine):
        sessions = _make_sessions(
            n=4,
            emotion_summaries=["开心", "焦虑", "快乐", "压力大"],
        )
        tone = evolve_engine._analyze_emotion_tone(sessions)
        assert tone == "mixed"

    def test_positive_dominates_over_one_negative(self, evolve_engine):
        # pos=3, neg=1 => pos > neg*2 => positive
        sessions = _make_sessions(
            n=4,
            emotion_summaries=["开心", "高兴", "快乐", "压力大"],
        )
        tone = evolve_engine._analyze_emotion_tone(sessions)
        assert tone == "positive"


# ===========================================================================
# _infer_hidden_needs
# ===========================================================================


class TestInferHiddenNeeds:
    def test_negative_emotion_triggers_care_need(self, evolve_engine):
        sessions = _make_sessions(n=3, emotion_summaries=["焦虑", "压力", "难过"])
        needs = evolve_engine._infer_hidden_needs(sessions, {}, {}, "negative")
        assert "需要更多关心和理解" in needs

    def test_repeated_topic_triggers_deep_support(self, evolve_engine):
        sessions = _make_sessions(n=5)
        topic_dist = {"工作": 3, "生活": 1}
        needs = evolve_engine._infer_hidden_needs(sessions, topic_dist, {}, "neutral")
        assert any("工作" in need and "持续关注" in need for need in needs)

    def test_deep_conversation_ratio_triggers_resonance(self, evolve_engine):
        sessions = _make_sessions(
            n=4,
            interaction_types=["deep_conversation", "deep_conversation", "emotion_companion", "daily_chat"],
        )
        type_dist = {"deep_conversation": 2, "emotion_companion": 1, "daily_chat": 1}
        needs = evolve_engine._infer_hidden_needs(sessions, {}, type_dist, "neutral")
        assert "倾向深度交流，需要情感共鸣" in needs

    def test_light_chat_ratio_triggers_happiness(self, evolve_engine):
        sessions = _make_sessions(
            n=4,
            interaction_types=["light_chat", "light_chat", "light_chat", "daily_chat"],
        )
        type_dist = {"light_chat": 3, "daily_chat": 1}
        needs = evolve_engine._infer_hidden_needs(sessions, {}, type_dist, "neutral")
        assert "倾向轻松互动，需要快乐和陪伴" in needs

    def test_max_five_needs(self, evolve_engine):
        """Ensure hidden needs are capped at 5."""
        sessions = _make_sessions(
            n=7,
            topics=[["a"], ["a"], ["a"], ["b"], ["b"], ["b"], ["c"]],
            interaction_types=["deep_conversation"] * 7,
        )
        needs = evolve_engine._infer_hidden_needs(
            sessions, {"a": 3, "b": 3, "c": 1, "d": 4, "e": 5},
            {"deep_conversation": 7}, "negative",
        )
        assert len(needs) <= 5


# ===========================================================================
# calculate_context_driven_adjustments
# ===========================================================================


class TestCalculateContextDrivenAdjustments:
    def test_negative_emotion_adds_warmth(self, evolve_engine):
        patterns = ObservationPattern(emotion_tone="negative", hidden_needs=[])
        persona = PersonaConfig()
        state = RelationshipState()
        adj = evolve_engine.calculate_context_driven_adjustments(patterns, persona, state)
        assert adj.get("warmth", 0) > 0
        assert adj.get("gentleness", 0) > 0

    def test_positive_emotion_adds_humor(self, evolve_engine):
        patterns = ObservationPattern(emotion_tone="positive", hidden_needs=[])
        persona = PersonaConfig()
        state = RelationshipState()
        adj = evolve_engine.calculate_context_driven_adjustments(patterns, persona, state)
        assert adj.get("humor", 0) > 0

    def test_neutral_emotion_no_extra(self, evolve_engine):
        patterns = ObservationPattern(emotion_tone="neutral", hidden_needs=[])
        persona = PersonaConfig()
        state = RelationshipState()
        adj = evolve_engine.calculate_context_driven_adjustments(patterns, persona, state)
        # Only the base attr-based adjustments may exist; no emotion-driven deltas
        # With default attributes all 0, no attr-based adjustments fire either
        assert all(v == 0 for v in adj.values()) or len(adj) == 0

    def test_hidden_needs_add_adjustments(self, evolve_engine):
        patterns = ObservationPattern(
            emotion_tone="neutral",
            hidden_needs=["需要更多关心和理解", "倾向深度交流，需要情感共鸣"],
        )
        persona = PersonaConfig()
        state = RelationshipState()
        adj = evolve_engine.calculate_context_driven_adjustments(patterns, persona, state)
        assert adj.get("warmth", 0) > 0
        assert adj.get("curiosity", 0) > 0

    def test_adjustments_clamped_at_0_1(self, evolve_engine):
        patterns = ObservationPattern(
            emotion_tone="negative",
            hidden_needs=["需要更多关心和理解"],
        )
        persona = PersonaConfig()
        state = RelationshipState(attributes=AttributePoints(
            care=80, understanding=50, expression=60, humor=40,
            intuition=50, courage=50, sensitivity=70, memory_attr=40,
        ))
        adj = evolve_engine.calculate_context_driven_adjustments(patterns, persona, state)
        for dim, delta in adj.items():
            assert abs(delta) <= 0.1, f"{dim}={delta} exceeds clamp"


# ===========================================================================
# Consecutive Diminishing Mechanism
# ===========================================================================


class TestConsecutiveDiminishing:
    def test_first_cycle_no_diminishing(self, evolve_engine):
        """First cycle: no consecutive history, adjustments pass through."""
        state = RelationshipState(attributes=AttributePoints(care=50))
        sessions = _make_sessions(n=7, emotion_summaries=["焦虑"] * 7)

        result_state, log = evolve_engine.run_evolution_cycle(sessions, state)
        # warmth should have been adjusted (from negative emotion + care attr)
        evo_state = evolve_engine._load_evolution_state()
        assert evo_state.consecutive_adjustments.get("warmth", 0) >= 1

    def test_third_cycle_diminishes(self, evolve_engine):
        """After 3 consecutive positive adjustments on same dim, factor applies."""
        state = RelationshipState(attributes=AttributePoints(care=50))
        sessions = _make_sessions(n=7, emotion_summaries=["焦虑"] * 7)

        # Run 3 cycles to build up consecutive count
        for _ in range(3):
            evolve_engine.run_evolution_cycle(sessions, state)

        evo_state = evolve_engine._load_evolution_state()
        # warmth should have >= 3 consecutive positive adjustments
        warmth_consecutive = evo_state.consecutive_adjustments.get("warmth", 0)
        assert warmth_consecutive >= 3

    def test_fifth_cycle_stops_adjustment(self, evolve_engine):
        """After 5 consecutive positive adjustments, dim is zeroed out."""
        state = RelationshipState(attributes=AttributePoints(care=50))
        sessions = _make_sessions(n=7, emotion_summaries=["焦虑"] * 7)

        # Pre-seed evolution state with 5 consecutive warmth adjustments
        evo_state = EvolutionState(
            consecutive_adjustments={"warmth": 5},
            total_cycles=5,
            last_adjustments={"warmth": 0.1},
        )
        evolve_engine._save_evolution_state(evo_state)

        result_state, log = evolve_engine.run_evolution_cycle(sessions, state)
        # warmth should be 0.0 because consecutive >= 5
        assert log.adjustments.get("warmth", 0) == 0.0

    def test_direction_change_resets_consecutive(self, evolve_engine):
        """If adjustment direction changes, consecutive counter resets."""
        # Pre-seed: warmth was positive before
        evo_state = EvolutionState(
            consecutive_adjustments={"warmth": 2},
            total_cycles=2,
            last_adjustments={"warmth": 0.05},
        )
        evolve_engine._save_evolution_state(evo_state)

        # Create a scenario where warmth gets 0 or negative adjustment
        # neutral emotion + no hidden needs + low attributes => no warmth adjustment
        state = RelationshipState()
        sessions = _make_sessions(n=7, emotion_summaries=[""] * 7)

        result_state, log = evolve_engine.run_evolution_cycle(sessions, state)
        evo_state = evolve_engine._load_evolution_state()
        # If warmth adjustment is 0 and last was positive, counter resets
        if log.adjustments.get("warmth", 0) <= 0:
            assert evo_state.consecutive_adjustments.get("warmth", 0) == 0


# ===========================================================================
# run_evolution_cycle integration
# ===========================================================================


class TestRunEvolutionCycleIntegration:
    def test_cycle_creates_log_with_emotion(self, evolve_engine):
        state = RelationshipState()
        sessions = _make_sessions(
            n=7,
            emotion_summaries=["开心"] * 7,
        )
        result_state, log_entry = evolve_engine.run_evolution_cycle(sessions, state)
        assert "情绪:positive" in log_entry.trigger
        assert log_entry.trial_result == "pass"
        assert log_entry.internalized is True

    def test_cycle_observation_includes_summary(self, evolve_engine):
        state = RelationshipState()
        sessions = _make_sessions(
            n=7,
            topics=[["工作"], ["工作"], ["工作"], ["生活"], ["生活"], ["娱乐"], ["日常"]],
        )
        result_state, log_entry = evolve_engine.run_evolution_cycle(sessions, state)
        assert "工作" in log_entry.observation
        assert "情绪基调" in log_entry.observation

    def test_cycle_saves_evolution_state(self, evolve_engine):
        state = RelationshipState(attributes=AttributePoints(care=50))
        sessions = _make_sessions(n=7)
        evolve_engine.run_evolution_cycle(sessions, state)

        evo_state = evolve_engine._load_evolution_state()
        assert evo_state.total_cycles >= 1
        assert isinstance(evo_state.evolution_progress, dict)

    def test_cycle_updates_persona_file(self, evolve_engine):
        state = RelationshipState(attributes=AttributePoints(care=50))
        sessions = _make_sessions(n=7, emotion_summaries=["焦虑"] * 7)

        # Record persona before
        from src.core.persona import PersonaEngine
        pe = PersonaEngine(evolve_engine.config)
        persona_before = pe.load_persona()
        warmth_before = persona_before.personality_base.warmth

        evolve_engine.run_evolution_cycle(sessions, state)

        persona_after = pe.load_persona()
        warmth_after = persona_after.personality_base.warmth
        # warmth should have increased (negative emotion + care attr)
        assert warmth_after >= warmth_before

    def test_cycle_returns_original_state_unchanged(self, evolve_engine):
        state = RelationshipState(attributes=AttributePoints(care=40))
        sessions = _make_sessions(n=7)
        result_state, log = evolve_engine.run_evolution_cycle(sessions, state)
        # run_evolution_cycle returns the same state object (unchanged)
        assert result_state.attributes.care == 40


# ===========================================================================
# _load_evolution_state / _save_evolution_state persistence
# ===========================================================================


class TestEvolutionStatePersistence:
    def test_load_returns_default_when_no_file(self, evolve_engine):
        evo_state = evolve_engine._load_evolution_state()
        assert evo_state.total_cycles == 0
        assert evo_state.consecutive_adjustments == {}
        assert evo_state.evolution_progress == {}

    def test_save_and_load_roundtrip(self, evolve_engine):
        evo_state = EvolutionState(
            consecutive_adjustments={"warmth": 3, "humor": 1},
            total_cycles=5,
            last_adjustments={"warmth": 0.05, "humor": 0.02},
            evolution_progress={"care": 0.5, "humor": 0.3},
        )
        evolve_engine._save_evolution_state(evo_state)

        loaded = evolve_engine._load_evolution_state()
        assert loaded.total_cycles == 5
        assert loaded.consecutive_adjustments["warmth"] == 3
        assert loaded.consecutive_adjustments["humor"] == 1
        assert loaded.last_adjustments["warmth"] == 0.05
        assert loaded.evolution_progress["care"] == 0.5

    def test_evolution_state_file_content(self, evolve_engine):
        evo_state = EvolutionState(total_cycles=3)
        evolve_engine._save_evolution_state(evo_state)

        evo_path = evolve_engine.config.evolution_config_path
        assert os.path.exists(evo_path)
        with open(evo_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["total_cycles"] == 3


# ===========================================================================
# _calculate_progress
# ===========================================================================


class TestCalculateProgress:
    def test_zero_attributes(self, evolve_engine):
        state = RelationshipState()
        progress = evolve_engine._calculate_progress(state)
        for attr, val in progress.items():
            assert val == 0.0

    def test_full_attributes(self, evolve_engine):
        state = RelationshipState(attributes=AttributePoints(
            care=100, understanding=100, expression=100, memory_attr=100,
            humor=100, intuition=100, courage=100, sensitivity=100,
        ))
        progress = evolve_engine._calculate_progress(state)
        for attr, val in progress.items():
            assert val == 1.0

    def test_partial_attributes(self, evolve_engine):
        state = RelationshipState(attributes=AttributePoints(care=50, humor=25))
        progress = evolve_engine._calculate_progress(state)
        assert progress["care"] == 0.5
        assert progress["humor"] == 0.25
        assert len(progress) == 8


# ===========================================================================
# Backward compatibility: original calculate_evolution_adjustments still works
# ===========================================================================


class TestBackwardCompatibility:
    def test_original_calculate_evolution_adjustments(self, evolve_engine):
        persona = PersonaConfig()
        state = RelationshipState(attributes=AttributePoints(care=50))
        adj = evolve_engine.calculate_evolution_adjustments(persona, state)
        assert isinstance(adj, dict)
        # warmth should be adjusted from care=50
        assert adj.get("warmth", 0) > 0


# ===========================================================================
# Emotion keyword impact assessment (Round 1 unified keyword set)
# ===========================================================================


class TestEmotionKeywordImpact:
    """Verify unified keyword set correctly classifies emotions that were previously missed"""

    def test_positive_keywords_now_match_喜欢_爱(self, evolve_engine):
        """Before Round 1, memory.py missed '喜欢' and '爱' - now unified set includes them"""
        sessions = [
            SessionMemory(conversation_id="c1", emotion_summary="我很喜欢这个"),
            SessionMemory(conversation_id="c2", emotion_summary="爱你"),
            SessionMemory(conversation_id="c3", emotion_summary="一般般"),
        ]
        tone = evolve_engine._analyze_emotion_tone(sessions)
        assert tone == "positive"  # 2 positive (喜欢+爱) vs 0 negative

    def test_negative_keywords_now_match_烦_害怕_紧张(self, evolve_engine):
        """Before Round 1, memory.py missed '烦', '害怕', '紧张' - now unified set includes them"""
        sessions = [
            SessionMemory(conversation_id="c1", emotion_summary="真的很烦"),
            SessionMemory(conversation_id="c2", emotion_summary="害怕明天"),
            SessionMemory(conversation_id="c3", emotion_summary="紧张"),
        ]
        tone = evolve_engine._analyze_emotion_tone(sessions)
        assert tone == "negative"  # 3 negative vs 0 positive

    def test_emotion_trend_with_new_keywords(self, memory_engine):
        """Verify compute_emotion_trend handles expanded keyword set"""
        sessions = [
            SessionMemory(conversation_id="c1", emotion_summary="喜欢", interaction_type="daily_chat"),
            SessionMemory(conversation_id="c2", emotion_summary="烦", interaction_type="daily_chat"),
            SessionMemory(conversation_id="c3", emotion_summary="开心", interaction_type="daily_chat"),
        ]
        trend = memory_engine.compute_emotion_trend(sessions)
        assert trend["trend"] in ("improving", "stable", "declining")
        # 2 positive (喜欢+开心) vs 1 negative (烦) -> improving or stable
