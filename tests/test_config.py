import os
import tempfile
from src.core.config import Config, get_config


class TestConfig:
    def test_default_data_dir(self):
        config = Config(data_dir=os.path.join(tempfile.gettempdir(), "gf-test-config"))
        assert config.data_dir.endswith("gf-test-config")

    def test_sub_dirs_created(self):
        with tempfile.TemporaryDirectory() as td:
            config = Config(data_dir=os.path.join(td, "gf-agent"))
            config.ensure_dirs()
            assert os.path.isdir(os.path.join(td, "gf-agent", "data", "chroma_db"))
            assert os.path.isdir(os.path.join(td, "gf-agent", "data", "session_memory"))
            assert os.path.isdir(os.path.join(td, "gf-agent", "data", "evolution_log"))
            assert os.path.isdir(os.path.join(td, "gf-agent", "data", "interaction_log"))
            assert os.path.isdir(os.path.join(td, "gf-agent", "config"))

    def test_interaction_type_values(self):
        assert "daily_chat" in Config.INTERACTION_TYPES
        assert "deep_conversation" in Config.INTERACTION_TYPES
        assert "collaborative_task" in Config.INTERACTION_TYPES
        assert "emotion_companion" in Config.INTERACTION_TYPES
        assert "light_chat" in Config.INTERACTION_TYPES

    def test_level_thresholds(self):
        assert Config.LEVEL_THRESHOLDS[0] == 0
        assert Config.LEVEL_THRESHOLDS[1] > 0
        assert len(Config.LEVEL_THRESHOLDS) == 7

    def test_intimacy_per_type(self):
        assert Config.INTIMACY_PER_TYPE["daily_chat"] == 1
        assert Config.INTIMACY_PER_TYPE["deep_conversation"] == 3
        assert Config.INTIMACY_PER_TYPE["collaborative_task"] == 5

    def test_get_config_singleton(self):
        with tempfile.TemporaryDirectory() as td:
            cfg1 = get_config(os.path.join(td, "gf-agent"))
            cfg2 = get_config(os.path.join(td, "gf-agent"))
            assert cfg1 is cfg2
