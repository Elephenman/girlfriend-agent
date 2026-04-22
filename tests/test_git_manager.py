import os
import json
import tempfile

import pytest

from src.core.git_manager import GitManager


@pytest.fixture
def git_mgr(temp_data_dir):
    mgr = GitManager(data_dir=temp_data_dir)
    mgr.init_repo()
    return mgr


class TestGitManagerInit:
    def test_init_creates_git_repo(self, temp_data_dir):
        mgr = GitManager(data_dir=temp_data_dir)
        mgr.init_repo()
        assert os.path.isdir(os.path.join(temp_data_dir, ".git"))

    def test_init_creates_gitignore(self, git_mgr, temp_data_dir):
        gitignore_path = os.path.join(temp_data_dir, ".gitignore")
        assert os.path.isfile(gitignore_path)
        with open(gitignore_path) as f:
            content = f.read()
        assert "chroma_db" in content
        assert "session_memory" in content

    def test_init_creates_initial_commit(self, git_mgr):
        log = git_mgr.log()
        assert len(log) >= 1
        assert "Lv0" in log[0]["message"]


class TestGitManagerCommit:
    def test_commit_config_files(self, git_mgr, temp_data_dir):
        config_dir = os.path.join(temp_data_dir, "config")
        os.makedirs(config_dir, exist_ok=True)
        with open(os.path.join(config_dir, "persona.json"), "w") as f:
            json.dump({"name": "test"}, f)
        git_mgr.commit("add persona")
        log = git_mgr.log()
        assert any("add persona" in entry["message"] for entry in log)

    def test_commit_evolution_log(self, git_mgr, temp_data_dir):
        evo_dir = os.path.join(temp_data_dir, "data", "evolution_log")
        os.makedirs(evo_dir, exist_ok=True)
        with open(os.path.join(evo_dir, "evo_001.json"), "w") as f:
            json.dump({"trigger": "test"}, f)
        git_mgr.commit("add evolution log")
        log = git_mgr.log()
        assert any("evolution log" in entry["message"] for entry in log)


class TestGitManagerLog:
    def test_log_returns_list(self, git_mgr):
        log = git_mgr.log()
        assert isinstance(log, list)
        assert len(log) >= 1
        assert "hash" in log[0]
        assert "message" in log[0]
        assert "date" in log[0]


class TestGitManagerCheckout:
    def test_checkout_restores_config(self, git_mgr, temp_data_dir):
        config_dir = os.path.join(temp_data_dir, "config")
        with open(os.path.join(config_dir, "persona.json"), "w") as f:
            json.dump({"name": "v1"}, f)
        git_mgr.commit("v1 persona")

        with open(os.path.join(config_dir, "persona.json"), "w") as f:
            json.dump({"name": "v2"}, f)
        git_mgr.commit("v2 persona")

        log = git_mgr.log()
        v1_hash = [e for e in log if "v1" in e["message"]][0]["hash"]
        git_mgr.checkout(v1_hash)

        with open(os.path.join(config_dir, "persona.json")) as f:
            data = json.load(f)
        assert data["name"] == "v1"
