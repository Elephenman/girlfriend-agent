# src/api/memory_router.py
from pydantic import BaseModel, Field, field_validator

from fastapi import APIRouter, Request

from src.core.models import MemoryUpdateRequest

router = APIRouter()


class MemorySearchRequest(BaseModel):
    query: str
    level: int = Field(default=1, ge=1, le=3)
    n: int = Field(default=5, gt=0)

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query must not be empty")
        return v


class MemoryReinforceRequest(BaseModel):
    chunk_id: str = Field(min_length=1)
    strength: float = Field(default=0.1, gt=0, le=1.0)


class EmotionTrendRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=50)


@router.post("/memory/update")
async def memory_update(req: MemoryUpdateRequest, request: Request):
    memory_engine = request.app.state.memory_engine
    chunk_id = memory_engine.store_memory(req.content, req.memory_type, req.metadata)
    return {"status": "ok", "chunk_id": chunk_id}


@router.post("/memory/search")
async def memory_search(req: MemorySearchRequest, request: Request):
    memory_engine = request.app.state.memory_engine
    results = memory_engine.search_memories(req.query, n=req.n, level=req.level)
    return {"results": results}


@router.post("/memory/reinforce")
async def reinforce_memory(req: MemoryReinforceRequest, request: Request):
    """强化记忆权重"""
    memory_engine = request.app.state.memory_engine
    memory_engine.reinforce_memory(req.chunk_id, req.strength)
    return {"status": "ok"}


@router.post("/memory/decay")
async def decay_memories(request: Request):
    """执行记忆衰减（向量记忆 + 图谱节点）"""
    memory_engine = request.app.state.memory_engine
    memory_engine.decay_all_weights()

    graph_engine = request.app.state.graph_engine
    graph_engine.decay_graph_weights()
    graph_engine.save_graph()

    return {"status": "ok"}


@router.post("/memory/emotion-trend")
async def emotion_trend(req: EmotionTrendRequest, request: Request):
    """获取情绪趋势"""
    memory_engine = request.app.state.memory_engine
    sessions = memory_engine.load_recent_sessions(count=req.count)
    trend = memory_engine.compute_emotion_trend(sessions)
    return trend
