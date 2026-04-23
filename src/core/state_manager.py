import json
import os

from src.core.config import Config
from src.core.models import PersonaConfig, RelationshipState


class StateManager:
    """Centralized state persistence and app.state synchronization"""

    def __init__(self, config: Config):
        self.config = config

    def save_persona(self, persona: PersonaConfig) -> None:
        os.makedirs(os.path.dirname(self.config.persona_config_path), exist_ok=True)
        with open(self.config.persona_config_path, "w", encoding="utf-8") as f:
            json.dump(persona.model_dump(), f, ensure_ascii=False, indent=2)

    def save_relationship(self, relationship: RelationshipState) -> None:
        os.makedirs(os.path.dirname(self.config.relationship_config_path), exist_ok=True)
        with open(self.config.relationship_config_path, "w", encoding="utf-8") as f:
            json.dump(relationship.model_dump(), f, ensure_ascii=False, indent=2)

    def load_persona(self) -> PersonaConfig:
        path = self.config.persona_config_path
        if not os.path.isfile(path):
            return PersonaConfig()
        with open(path, encoding="utf-8") as f:
            return PersonaConfig(**json.load(f))

    def load_relationship(self) -> RelationshipState:
        path = self.config.relationship_config_path
        if not os.path.isfile(path):
            return RelationshipState()
        with open(path, encoding="utf-8") as f:
            return RelationshipState(**json.load(f))

    def reload_all(self, app) -> None:
        """Reload persona and relationship from disk and sync to app.state"""
        app.state.persona = self.load_persona()
        app.state.relationship = self.load_relationship()

    def persist_relationship(self, app) -> None:
        """Write current app.state.relationship to disk"""
        self.save_relationship(app.state.relationship)