# src/api/status_router.py
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/status")
async def status(request: Request):
    rel = request.app.state.relationship
    return {
        "current_level": rel.current_level,
        "intimacy_points": rel.intimacy_points,
        "attributes": rel.attributes.model_dump(),
        "de_ai_score": rel.de_ai_score.model_dump(),
        "nickname": rel.nickname,
        "conflict_mode": rel.conflict_mode,
        "shared_jokes": rel.shared_jokes,
        "rituals": rel.rituals,
    }


@router.get("/health")
async def health(request: Request):
    memory_engine = request.app.state.memory_engine
    embedding_loaded = False
    try:
        embedding_loaded = memory_engine.collection is not None
    except Exception:
        pass
    return {"status": "ok", "embedding_loaded": embedding_loaded}
