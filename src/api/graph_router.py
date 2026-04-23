# src/api/graph_router.py
from pydantic import BaseModel, Field, field_validator

from fastapi import APIRouter, Request

router = APIRouter()


class GraphAddEntityRequest(BaseModel):
    entity_name: str = Field(min_length=1)
    entity_type: str = Field(default="entity")
    properties: dict = Field(default_factory=dict)

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        valid = {"entity", "event", "topic", "emotion"}
        if v not in valid:
            raise ValueError(f"entity_type must be one of {valid}, got '{v}'")
        return v


class GraphAddRelationRequest(BaseModel):
    source_entity: str = Field(min_length=1)
    target_entity: str = Field(min_length=1)
    relation_type: str = Field(default="related_to")
    properties: dict = Field(default_factory=dict)

    @field_validator("relation_type")
    @classmethod
    def validate_relation_type(cls, v: str) -> str:
        valid = {"caused", "related_to", "followed_by", "about", "felt_during"}
        if v not in valid:
            raise ValueError(f"relation_type must be one of {valid}, got '{v}'")
        return v


class GraphAddEventRequest(BaseModel):
    description: str = Field(min_length=1)
    entities: list[str] = Field(default_factory=list)
    timestamp: str | None = None
    emotion: str = Field(default="")


class GraphSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    max_depth: int = Field(default=3, ge=1, le=10)
    max_nodes: int = Field(default=20, ge=1, le=100)


class GraphTimelineRequest(BaseModel):
    entity_id: str = Field(min_length=1)


class GraphBatchBuildRequest(BaseModel):
    session_count: int = Field(default=7, ge=1, le=30)


@router.post("/graph/add-entity")
async def graph_add_entity(req: GraphAddEntityRequest, request: Request):
    builder = request.app.state.episodic_builder
    node_id = builder.add_entity(req.entity_name, req.entity_type, req.properties)
    graph_engine = request.app.state.graph_engine
    graph_engine.save_graph()
    return {"status": "ok", "node_id": node_id}


@router.post("/graph/add-relation")
async def graph_add_relation(req: GraphAddRelationRequest, request: Request):
    builder = request.app.state.episodic_builder
    success = builder.add_relation(req.source_entity, req.target_entity, req.relation_type, req.properties)
    graph_engine = request.app.state.graph_engine
    graph_engine.save_graph()
    return {"status": "ok" if success else "error"}


@router.post("/graph/add-event")
async def graph_add_event(req: GraphAddEventRequest, request: Request):
    builder = request.app.state.episodic_builder
    event_id = builder.add_event(req.description, req.entities, req.timestamp, req.emotion)
    graph_engine = request.app.state.graph_engine
    graph_engine.save_graph()
    return {"status": "ok", "event_id": event_id}


@router.post("/graph/search")
async def graph_search(req: GraphSearchRequest, request: Request):
    graph_engine = request.app.state.graph_engine
    result = graph_engine.search_graph(req.query, req.max_depth, req.max_nodes)
    return result.model_dump()


@router.post("/graph/timeline")
async def graph_timeline(req: GraphTimelineRequest, request: Request):
    graph_engine = request.app.state.graph_engine
    timeline = graph_engine.get_timeline(req.entity_id)
    return {"timeline": timeline}


@router.post("/graph/batch-build")
async def graph_batch_build(req: GraphBatchBuildRequest, request: Request):
    memory_engine = request.app.state.memory_engine
    sessions = memory_engine.load_recent_sessions(count=req.session_count)
    builder = request.app.state.episodic_builder
    stats = builder.batch_build(sessions)
    return {"status": "ok", "stats": stats}


@router.get("/graph/stats")
async def graph_stats(request: Request):
    graph_engine = request.app.state.graph_engine
    return graph_engine.get_stats()