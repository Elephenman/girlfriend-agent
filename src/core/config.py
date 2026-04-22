import os
from pathlib import Path


class Config:
    DATA_DIR_NAME = ".girlfriend-agent"
    SERVER_PORT = 18012

    INTERACTION_TYPES = {
        "daily_chat",
        "deep_conversation",
        "collaborative_task",
        "emotion_companion",
        "light_chat",
    }

    INTIMACY_PER_TYPE = {
        "daily_chat": 1,
        "deep_conversation": 3,
        "collaborative_task": 5,
        "emotion_companion": 4,
        "light_chat": 1,
    }

    ATTRIBUTE_PER_TYPE = {
        "daily_chat": {"care": 0.5, "understanding": 0.5, "expression": 0.5, "memory_attr": 0.5, "humor": 0.5, "intuition": 0.5, "courage": 0.5, "sensitivity": 0.5},
        "deep_conversation": {"care": 1, "understanding": 1, "sensitivity": 1},
        "collaborative_task": {"understanding": 1, "courage": 1, "memory_attr": 1},
        "emotion_companion": {"care": 1.5, "sensitivity": 1, "expression": 0.5},
        "light_chat": {"humor": 1, "expression": 0.5, "courage": 0.5},
    }

    LEVEL_THRESHOLDS = [0, 10, 30, 60, 100, 160, 240]

    EVOLUTION_CYCLE_INTERVAL = 7

    MAX_RELATIVE_CHANGE = 0.10
    CONSECUTIVE_DIMINISH_AFTER = 3
    CONSECUTIVE_DIMINISH_FACTOR = 0.5

    WEIGHT_DECAY_LAMBDA = 0.1
    WEIGHT_ACCESS_SCALE = "sqrt"

    INJECTION_LEVELS = {
        1: {"max_memories": 3, "approx_chars": 600},
        2: {"max_memories": 8, "approx_chars": 2500},
        3: {"max_memories": 15, "approx_chars": 5000},
    }

    def __init__(self, data_dir: str | None = None):
        if data_dir is None:
            data_dir = os.path.join(str(Path.home()), self.DATA_DIR_NAME)
        self.data_dir = data_dir

    @property
    def chroma_db_dir(self) -> str:
        return os.path.join(self.data_dir, "data", "chroma_db")

    @property
    def session_memory_dir(self) -> str:
        return os.path.join(self.data_dir, "data", "session_memory")

    @property
    def evolution_log_dir(self) -> str:
        return os.path.join(self.data_dir, "data", "evolution_log")

    @property
    def interaction_log_dir(self) -> str:
        return os.path.join(self.data_dir, "data", "interaction_log")

    @property
    def config_dir(self) -> str:
        return os.path.join(self.data_dir, "config")

    @property
    def persona_config_path(self) -> str:
        return os.path.join(self.config_dir, "persona.json")

    @property
    def relationship_config_path(self) -> str:
        return os.path.join(self.config_dir, "relationship.json")

    @property
    def evolution_config_path(self) -> str:
        return os.path.join(self.config_dir, "evolution.json")

    @property
    def de_ai_config_path(self) -> str:
        return os.path.join(self.config_dir, "de_ai_dimensions.json")

    @property
    def attribute_points_config_path(self) -> str:
        return os.path.join(self.config_dir, "attribute_points.json")

    @property
    def settings_config_path(self) -> str:
        return os.path.join(self.config_dir, "settings.json")

    @property
    def level_prompts_dir(self) -> str:
        return os.path.join(self.config_dir, "level_prompts")

    @property
    def templates_dir(self) -> str:
        return os.path.join(self.data_dir, "templates")

    def ensure_dirs(self) -> None:
        for d in [
            self.chroma_db_dir,
            self.session_memory_dir,
            self.evolution_log_dir,
            self.interaction_log_dir,
            self.config_dir,
            self.level_prompts_dir,
            self.templates_dir,
        ]:
            os.makedirs(d, exist_ok=True)


_config_instance: Config | None = None


def get_config(data_dir: str | None = None) -> Config:
    global _config_instance
    if _config_instance is None or (data_dir is not None and _config_instance.data_dir != data_dir):
        _config_instance = Config(data_dir)
    return _config_instance
