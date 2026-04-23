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
async def reinforce_memory(request: Request):
    """强化记忆权重"""
    body = await request.json()
    chunk_id = body.get("chunk_id", "")
    strength = body.get("strength", 0.1)
    memory_engine = request.app.state.memory_engine
    memory_engine.reinforce_memory(chunk_id, strength)
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
async def emotion_trend(request: Request):
    """获取情绪趋势"""
    body = await request.json()
    count = body.get("count", 10)
    memory_engine = request.app.state.memory_engine
    sessions = memory_engine.load_recent_sessions(count=count)
    trend = memory_engine.compute_emotion_trend(sessions)
    return trend


# 图记忆相关API
@router.post("/graph/add-entity")
async def graph_add_entity(request: Request):
    """添加实体节点到图谱"""
    body = await request.json()
    entity_name = body.get("entity_name", "")
    entity_type = body.get("entity_type", "entity")
    properties = body.get("properties", {})

    builder = request.app.state.episodic_builder
    node_id = builder.add_entity(entity_name, entity_type, properties)

    graph_engine = request.app.state.graph_engine
    graph_engine.save_graph()
    return {"status": "ok", "node_id": node_id}


@router.post("/graph/add-relation")
async def graph_add_relation(request: Request):
    """添加关系边到图谱"""
    body = await request.json()
    source = body.get("source_entity", "")
    target = body.get("target_entity", "")
    relation_type = body.get("relation_type", "related_to")
    properties = body.get("properties", {})

    builder = request.app.state.episodic_builder
    success = builder.add_relation(source, target, relation_type, properties)

    graph_engine = request.app.state.graph_engine
    graph_engine.save_graph()
    return {"status": "ok" if success else "error"}


@router.post("/graph/add-event")
async def graph_add_event(request: Request):
    """添加事件到图谱"""
    body = await request.json()
    event_desc = body.get("description", "")
    related_entities = body.get("entities", [])
    timestamp = body.get("timestamp")
    emotion = body.get("emotion", "")

    builder = request.app.state.episodic_builder
    event_id = builder.add_event(event_desc, related_entities, timestamp, emotion)

    graph_engine = request.app.state.graph_engine
    graph_engine.save_graph()
    return {"status": "ok", "event_id": event_id}


@router.post("/graph/search")
async def graph_search(request: Request):
    """搜索图谱"""
    body = await request.json()
    query = body.get("query", "")
    max_depth = body.get("max_depth", 3)
    max_nodes = body.get("max_nodes", 20)

    graph_engine = request.app.state.graph_engine
    result = graph_engine.search_graph(query, max_depth, max_nodes)
    return result.model_dump()


@router.post("/graph/timeline")
async def graph_timeline(request: Request):
    """获取实体时间线"""
    body = await request.json()
    entity_id = body.get("entity_id", "")

    graph_engine = request.app.state.graph_engine
    timeline = graph_engine.get_timeline(entity_id)
    return {"timeline": timeline}


@router.post("/graph/batch-build")
async def graph_batch_build(request: Request):
    """批量建图"""
    body = await request.json()
    session_count = body.get("session_count", 7)

    memory_engine = request.app.state.memory_engine
    sessions = memory_engine.load_recent_sessions(count=session_count)

    builder = request.app.state.episodic_builder
    stats = builder.batch_build(sessions)
    return {"status": "ok", "stats": stats}


@router.get("/graph/stats")
async def graph_stats(request: Request):
    """获取图谱统计"""
    graph_engine = request.app.state.graph_engine
    return graph_engine.get_stats()
