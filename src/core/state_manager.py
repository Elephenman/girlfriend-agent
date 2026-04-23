import json
import os

from src.core.config import Config
from src.core.models import PersonaConfig, RelationshipState


class StateManager:
    """Centralized state persistence and app.state synchronization.

    Method usage convention:
    - load_or_init_*: Used in lifespan initialization. Returns default + persists if file missing (self-heal).
    - load_*: Used in reload scenarios (e.g., after git revert). Returns default if file missing, NO persist.
    - save_*: Explicit persist of a given model object.
    - reload_all: Reload both persona and relationship from disk, sync to app.state.
    - persist_relationship: Write current app.state.relationship to disk.
    """

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
        """Load persona from disk.

        For reload scenarios only. If file missing, returns PersonaConfig() without persist.
        Use load_or_init_persona() for initialization (which self-heals on missing file).
        """
        path = self.config.persona_config_path
        if not os.path.isfile(path):
            return PersonaConfig()
        with open(path, encoding="utf-8") as f:
            return PersonaConfig(**json.load(f))

    def load_relationship(self) -> RelationshipState:
        """Load relationship from disk.

        For reload scenarios only. If file missing, returns RelationshipState() without persist.
        Use load_or_init_relationship() for initialization (which self-heals on missing file).
        """
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

    def load_or_init_persona(self) -> PersonaConfig:
        """Load persona from disk; if file missing, create default and persist (self-heal).

        For lifespan initialization. Guarantees file exists after call.
        """
        path = self.config.persona_config_path
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return PersonaConfig(**json.load(f))
        persona = PersonaConfig()
        self.save_persona(persona)
        return persona

    def load_or_init_relationship(self) -> RelationshipState:
        """Load relationship from disk; if file missing, create default and persist (self-heal).

        For lifespan initialization. Guarantees file exists after call.
        """
        path = self.config.relationship_config_path
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return RelationshipState(**json.load(f))
        relationship = RelationshipState()
        self.save_relationship(relationship)
        return relationship