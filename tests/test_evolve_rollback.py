import json
import os
import tempfile

import pytest

from src.core.config import Config
from src.core.evolve import EvolveEngine
from src.core.git_manager import GitManager
from src.core.models import (
    RelationshipState, AttributePoints, SessionMemory,
    PersonaConfig, PersonalityBase, EvolutionState,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_data_dir():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        data_dir = os.path.join(td, "gf-agent")
        config = Config(data_dir=data_dir)
        config.ensure_dirs()
        yield data_dir


@pytest.fixture
def config(temp_data_dir):
    return Config(data_dir=temp_data_dir)


@pytest.fixture
def git_mgr(temp_data_dir):
    mgr = GitManager(data_dir=temp_data_dir)
    mgr.init_repo()
    return mgr


@pytest.fixture
def evolve_engine(temp_data_dir, git_mgr):
    config = Config(data_dir=temp_data_dir)
    engine = EvolveEngine(config, git_mgr)
    return engine


def _write_persona(config: Config, persona: PersonaConfig) -> None:
    with open(config.persona_config_path, "w", encoding="utf-8") as f:
        json.dump(persona.model_dump(), f, ensure_ascii=False, indent=2)


def _run_one_evolution(evolve_engine, git_mgr, config):
    """Helper: run one evolution cycle and return the log entry."""
    state = RelationshipState(
        attributes=AttributePoints(care=50, sensitivity=50),
    )
    sessions = [
        SessionMemory(conversation_id=f"c-{i}", topics=["test"],
                      interaction_type="daily_chat")
        for i in range(7)
    ]
    _, log_entry = evolve_engine.run_evolution_cycle(sessions, state)
    return log_entry


# ---------------------------------------------------------------------------
# TestGitManager: get_evolution_commits
# ---------------------------------------------------------------------------

class TestGetEvolutionCommits:
    def test_empty_when_no_evolution_commits(self, git_mgr):
        commits = git_mgr.get_evolution_commits()
        assert commits == []

    def test_finds_evolution_commits(self, git_mgr, temp_data_dir):
        # Create a file and commit with "evolution:" prefix
        config_dir = os.path.join(temp_data_dir, "config")
        with open(os.path.join(config_dir, "persona.json"), "w") as f:
            json.dump({"name": "test"}, f)
        git_mgr.commit("evolution: test cycle")

        commits = git_mgr.get_evolution_commits()
        assert len(commits) == 1
        assert commits[0]["message"].startswith("evolution:")
        assert "hash" in commits[0]
        assert "date" in commits[0]

    def test_excludes_non_evolution_commits(self, git_mgr, temp_data_dir):
        config_dir = os.path.join(temp_data_dir, "config")
        with open(os.path.join(config_dir, "persona.json"), "w") as f:
            json.dump({"name": "test"}, f)
        git_mgr.commit("some other commit")

        commits = git_mgr.get_evolution_commits()
        assert commits == []

    def test_multiple_evolution_commits(self, git_mgr, temp_data_dir):
        config_dir = os.path.join(temp_data_dir, "config")
        for i in range(3):
            with open(os.path.join(config_dir, f"file_{i}.json"), "w") as f:
                json.dump({"i": i}, f)
            git_mgr.commit(f"evolution: cycle {i}")

        commits = git_mgr.get_evolution_commits()
        assert len(commits) == 3
        # Most recent first
        assert "cycle 2" in commits[0]["message"]
        assert "cycle 0" in commits[2]["message"]


# ---------------------------------------------------------------------------
# TestGitManager: revert_evolution_commit
# ---------------------------------------------------------------------------

class TestRevertEvolutionCommit:
    def test_revert_latest_evolution(self, git_mgr, temp_data_dir):
        config_dir = os.path.join(temp_data_dir, "config")
        # Initial persona
        with open(os.path.join(config_dir, "persona.json"), "w") as f:
            json.dump({"warmth": 0.5}, f)
        git_mgr.commit("evolution: first")

        # Modify persona
        with open(os.path.join(config_dir, "persona.json"), "w") as f:
            json.dump({"warmth": 0.7}, f)
        git_mgr.commit("evolution: second")

        # Revert latest evolution
        result = git_mgr.revert_evolution_commit()
        assert result is True

        # persona.json should be back to warmth=0.5
        with open(os.path.join(config_dir, "persona.json")) as f:
            data = json.load(f)
        assert data["warmth"] == 0.5

    def test_revert_specific_commit(self, git_mgr, temp_data_dir):
        config_dir = os.path.join(temp_data_dir, "config")
        with open(os.path.join(config_dir, "persona.json"), "w") as f:
            json.dump({"warmth": 0.3}, f)
        git_mgr.commit("evolution: first")

        with open(os.path.join(config_dir, "persona.json"), "w") as f:
            json.dump({"warmth": 0.8}, f)
        git_mgr.commit("evolution: second")

        # Revert the latest (second) commit by its specific hash
        commits = git_mgr.get_evolution_commits()
        target_hash = commits[0]["hash"]  # most recent = "second"
        result = git_mgr.revert_evolution_commit(commit_hash=target_hash)
        assert result is True

        # persona.json should be back to warmth=0.3
        with open(os.path.join(config_dir, "persona.json")) as f:
            data = json.load(f)
        assert data["warmth"] == 0.3

    def test_revert_returns_false_when_no_evolution(self, git_mgr):
        result = git_mgr.revert_evolution_commit()
        assert result is False


# ---------------------------------------------------------------------------
# TestEvolveEngine: revert_last_evolution
# ---------------------------------------------------------------------------

class TestRevertLastEvolution:
    def test_revert_success(self, evolve_engine, git_mgr, config):
        # Write initial persona
        initial_persona = PersonaConfig(
            personality_base=PersonalityBase(warmth=0.5)
        )
        _write_persona(config, initial_persona)

        # Run an evolution cycle
        state = RelationshipState(
            attributes=AttributePoints(care=50, sensitivity=50),
        )
        sessions = [
            SessionMemory(conversation_id=f"c-{i}", topics=["test"],
                          interaction_type="daily_chat")
            for i in range(7)
        ]
        evolve_engine.run_evolution_cycle(sessions, state)

        # Now revert
        result = evolve_engine.revert_last_evolution()
        assert result["success"] is True
        assert "已回退" in result["message"]
        assert "current_persona" in result

    def test_revert_resets_evolution_state(self, evolve_engine, git_mgr, config):
        # Write persona and set up evolution state with some data
        initial_persona = PersonaConfig()
        _write_persona(config, initial_persona)

        # Create an evolution state file with data
        evo_state = EvolutionState(
            consecutive_adjustments={"warmth": 3},
            total_cycles=5,
            last_adjustments={"warmth": 0.05},
        )
        evo_path = config.evolution_config_path
        with open(evo_path, "w", encoding="utf-8") as f:
            json.dump(evo_state.model_dump(), f, ensure_ascii=False, indent=2)

        # Run an evolution cycle
        state = RelationshipState(
            attributes=AttributePoints(care=50, sensitivity=50),
        )
        sessions = [
            SessionMemory(conversation_id=f"c-{i}", topics=["test"],
                          interaction_type="daily_chat")
            for i in range(7)
        ]
        evolve_engine.run_evolution_cycle(sessions, state)

        # Revert
        result = evolve_engine.revert_last_evolution()
        assert result["success"] is True

        # Check evolution state was reset
        with open(evo_path, encoding="utf-8") as f:
            evo_data = json.load(f)
        assert evo_data["consecutive_adjustments"] == {}
        assert evo_data["last_adjustments"] == {}

    def test_revert_no_evolution_commits(self, evolve_engine):
        result = evolve_engine.revert_last_evolution()
        assert result["success"] is False
        assert "没有可回退" in result["message"]


# ---------------------------------------------------------------------------
# TestEvolveEngine: revert_to_version
# ---------------------------------------------------------------------------

class TestRevertToVersion:
    def test_revert_to_specific_version(self, evolve_engine, git_mgr, config):
        # Write initial persona
        persona_v1 = PersonaConfig(
            personality_base=PersonalityBase(warmth=0.3)
        )
        _write_persona(config, persona_v1)
        git_mgr.commit("evolution: v1")

        # Get the commit hash
        commits = git_mgr.get_evolution_commits()
        v1_hash = commits[0]["hash"]

        # Modify persona
        persona_v2 = PersonaConfig(
            personality_base=PersonalityBase(warmth=0.8)
        )
        _write_persona(config, persona_v2)
        git_mgr.commit("evolution: v2")

        # Revert to v1
        result = evolve_engine.revert_to_version(v1_hash)
        assert result["success"] is True
        assert v1_hash[:8] in result["message"]

    def test_revert_to_version_invalid_hash(self, evolve_engine):
        result = evolve_engine.revert_to_version("invalid_hash_1234")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# TestEvolveEngine: evaluate_trial_result
# ---------------------------------------------------------------------------

class TestEvaluateTrialResult:
    def test_pass_when_emotion_improves(self, evolve_engine):
        before = [
            SessionMemory(conversation_id="c1", emotion_summary="neutral"),
            SessionMemory(conversation_id="c2", emotion_summary="neutral"),
        ]
        after = [
            SessionMemory(conversation_id="c3", emotion_summary="开心"),
            SessionMemory(conversation_id="c4", emotion_summary="高兴"),
        ]
        result = evolve_engine.evaluate_trial_result(after, before)
        assert result == "pass"

    def test_pass_when_interaction_increases(self, evolve_engine):
        before = [
            SessionMemory(conversation_id="c1", emotion_summary="neutral"),
        ]
        after = [
            SessionMemory(conversation_id="c2", emotion_summary="neutral"),
            SessionMemory(conversation_id="c3", emotion_summary="neutral"),
        ]
        result = evolve_engine.evaluate_trial_result(after, before)
        assert result == "pass"

    def test_negative_when_interaction_drops(self, evolve_engine):
        before = [
            SessionMemory(conversation_id=f"c{i}", emotion_summary="neutral")
            for i in range(10)
        ]
        after = [
            SessionMemory(conversation_id="c1", emotion_summary="neutral"),
            SessionMemory(conversation_id="c2", emotion_summary="neutral"),
        ]
        result = evolve_engine.evaluate_trial_result(after, before)
        assert result == "negative"

    def test_negative_when_emotion_drops(self, evolve_engine):
        before = [
            SessionMemory(conversation_id="c1", emotion_summary="开心"),
            SessionMemory(conversation_id="c2", emotion_summary="满意"),
        ]
        after = [
            SessionMemory(conversation_id="c3", emotion_summary="焦虑"),
            SessionMemory(conversation_id="c4", emotion_summary="难过"),
        ]
        result = evolve_engine.evaluate_trial_result(after, before)
        assert result == "negative"

    def test_neutral_when_no_change(self, evolve_engine):
        before = [
            SessionMemory(conversation_id="c1", emotion_summary="neutral"),
            SessionMemory(conversation_id="c2", emotion_summary="neutral"),
        ]
        after = [
            SessionMemory(conversation_id="c3", emotion_summary="neutral"),
            SessionMemory(conversation_id="c4", emotion_summary="neutral"),
        ]
        result = evolve_engine.evaluate_trial_result(after, before)
        assert result == "neutral"

    def test_neutral_when_no_after_sessions(self, evolve_engine):
        before = [
            SessionMemory(conversation_id="c1", emotion_summary="开心"),
        ]
        result = evolve_engine.evaluate_trial_result([], before)
        assert result == "neutral"


# ---------------------------------------------------------------------------
# TestGitignore: graphrag_db included
# ---------------------------------------------------------------------------

class TestGitignoreGraphragDb:
    def test_gitignore_includes_graphrag_db(self, temp_data_dir):
        mgr = GitManager(data_dir=temp_data_dir)
        mgr.init_repo()
        gitignore_path = os.path.join(temp_data_dir, ".gitignore")
        with open(gitignore_path, encoding="utf-8") as f:
            content = f.read()
        assert "graphrag_db/" in content
        assert "chroma_db/" in content
        assert "session_memory/" in content
