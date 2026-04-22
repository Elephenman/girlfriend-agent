# src/api/memory_router.py
from fastapi import APIRouter, Request

from src.core.models import MemoryUpdateRequest

router = APIRouter()


@router.post("/memory/update")
async def memory_update(req: MemoryUpdateRequest, request: Request):
    memory_engine = request.app.state.memory_engine
    chunk_id = memory_engine.store_memory(req.content, req.memory_type, req.metadata)
    return {"status": "ok", "chunk_id": chunk_id}


@router.post("/memory/search")
async def memory_search(request: Request):
    body = await request.json()
    query = body.get("query", "")
    level = body.get("level", 1)
    n = body.get("n", 5)
    memory_engine = request.app.state.memory_engine
    results = memory_engine.search_memories(query, n=n, level=level)
    return {"results": results}
