# src/api/rollback_router.py
from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/rollback")
async def rollback(request: Request):
    body = await request.json()
    commit_hash = body.get("commit_hash", "")

    app = request.app
    git_manager = app.state.git_manager

    git_manager.checkout(commit_hash)

    request.app.state.state_manager.reload_all(request.app)

    return {"status": "ok", "commit_hash": commit_hash}
