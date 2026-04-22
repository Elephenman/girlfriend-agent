# src/api/evolve_router.py
import json

from fastapi import APIRouter, Request

from src.core.models import SessionMemory

router = APIRouter()


@router.post("/evolve")
async def evolve(request: Request):
    app = request.app
    evolve_engine = app.state.evolve_engine
    memory_engine = app.state.memory_engine
    config = app.state.config
    relationship = app.state.relationship

    sessions = memory_engine.load_recent_sessions(count=7)

    if len(sessions) < 1:
        sessions = [SessionMemory(conversation_id="auto", interaction_type="daily_chat")]

    relationship, log_entry = evolve_engine.run_evolution_cycle(sessions, relationship)

    app.state.relationship = relationship
    with open(config.relationship_config_path, "w", encoding="utf-8") as f:
        json.dump(relationship.model_dump(), f, ensure_ascii=False, indent=2)

    return {
        "adjustments": log_entry.adjustments,
        "observation": log_entry.observation,
        "trigger": log_entry.trigger,
        "level": relationship.current_level,
        "intimacy": relationship.intimacy_points,
    }
