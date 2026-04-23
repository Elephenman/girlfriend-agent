# src/engine_server.py
import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import Config, get_config
from src.core.persona import PersonaEngine
from src.core.memory import MemoryEngine
from src.core.evolve import EvolveEngine
from src.core.git_manager import GitManager
from src.core.graph_memory import GraphMemoryEngine
from src.core.episodic_builder import EpisodicBuilder
from src.core.state_manager import StateManager
from src.core.models import PersonaConfig, RelationshipState

from src.api.chat_router import router as chat_router
from src.api.status_router import router as status_router
from src.api.evolve_router import router as evolve_router
from src.api.memory_router import router as memory_router
from src.api.persona_router import router as persona_router
from src.api.rollback_router import router as rollback_router


def _load_or_init_state(config: Config) -> tuple[PersonaConfig, RelationshipState]:
    # Load or self-heal persona
    if os.path.isfile(config.persona_config_path):
        with open(config.persona_config_path, encoding="utf-8") as f:
            persona = PersonaConfig(**json.load(f))
    else:
        persona = PersonaConfig()
        os.makedirs(os.path.dirname(config.persona_config_path), exist_ok=True)
        with open(config.persona_config_path, "w", encoding="utf-8") as f:
            json.dump(persona.model_dump(), f, ensure_ascii=False, indent=2)

    # Load or self-heal relationship
    if os.path.isfile(config.relationship_config_path):
        with open(config.relationship_config_path, encoding="utf-8") as f:
            relationship = RelationshipState(**json.load(f))
    else:
        relationship = RelationshipState()
        os.makedirs(os.path.dirname(config.relationship_config_path), exist_ok=True)
        with open(config.relationship_config_path, "w", encoding="utf-8") as f:
            json.dump(relationship.model_dump(), f, ensure_ascii=False, indent=2)

    return persona, relationship


def _save_state(config: Config, persona: PersonaConfig, relationship: RelationshipState) -> None:
    os.makedirs(os.path.dirname(config.persona_config_path), exist_ok=True)
    with open(config.persona_config_path, "w", encoding="utf-8") as f:
        json.dump(persona.model_dump(), f, ensure_ascii=False, indent=2)
    with open(config.relationship_config_path, "w", encoding="utf-8") as f:
        json.dump(relationship.model_dump(), f, ensure_ascii=False, indent=2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()
    config.ensure_dirs()

    git_mgr = GitManager(data_dir=config.data_dir)
    git_mgr.init_repo()

    state_mgr = StateManager(config)

    persona, relationship = _load_or_init_state(config)
    # _load_or_init_state handles self-heal saving internally

    app.state.config = config
    app.state.persona = persona
    app.state.relationship = relationship
    app.state.persona_engine = PersonaEngine(config)
    app.state.memory_engine = MemoryEngine(config)
    app.state.evolve_engine = EvolveEngine(config, git_mgr)
    app.state.git_manager = git_mgr
    app.state.state_manager = state_mgr
    app.state.graph_engine = GraphMemoryEngine(config)
    app.state.episodic_builder = EpisodicBuilder(config, app.state.graph_engine)

    yield

    # Graceful shutdown: persist graph to disk
    try:
        app.state.graph_engine.save_graph()
    except Exception:
        pass


app = FastAPI(title="girlfriend-agent", version="0.1.0", lifespan=lifespan)

app.include_router(chat_router, tags=["chat"])
app.include_router(status_router, tags=["status"])
app.include_router(evolve_router, tags=["evolve"])
app.include_router(memory_router, tags=["memory"])
app.include_router(persona_router, tags=["persona"])
app.include_router(rollback_router, tags=["rollback"])


def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=Config.SERVER_PORT)


if __name__ == "__main__":
    main()
