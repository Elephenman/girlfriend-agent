# src/api/rollback_router.py
import json
import os

from fastapi import APIRouter, Request

from src.core.models import PersonaConfig, RelationshipState

router = APIRouter()


@router.post("/rollback")
async def rollback(request: Request):
    body = await request.json()
    commit_hash = body.get("commit_hash", "")

    app = request.app
    config = app.state.config
    git_manager = app.state.git_manager

    git_manager.checkout(commit_hash)

    persona_path = config.persona_config_path
    if os.path.isfile(persona_path):
        with open(persona_path, encoding="utf-8") as f:
            data = json.load(f)
        app.state.persona = PersonaConfig(**data)

    rel_path = config.relationship_config_path
    if os.path.isfile(rel_path):
        with open(rel_path, encoding="utf-8") as f:
            data = json.load(f)
        app.state.relationship = RelationshipState(**data)

    return {"status": "ok", "commit_hash": commit_hash}
