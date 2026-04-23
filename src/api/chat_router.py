# src/api/chat_router.py
from fastapi import APIRouter, Request

from src.core.chat_service import ChatService
from src.core.models import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    app = request.app
    chat_service = ChatService(
        persona_engine=app.state.persona_engine,
        memory_engine=app.state.memory_engine,
        evolve_engine=app.state.evolve_engine,
        graph_engine=getattr(app.state, "graph_engine", None),
    )

    # Phase 1: State mutation under lock (minimal hold time)
    async with app.state.state_lock:
        relationship = chat_service.mutate_state(
            req, app.state.persona, app.state.relationship
        )
        # Commit state mutation and persist
        app.state.relationship = relationship
        app.state.state_manager.persist_relationship(app)

    # Phase 2: Build context outside lock (using committed snapshot)
    ctx = chat_service.build_context(req, app.state.persona, relationship)

    # Phase 3: Build response
    return ChatResponse(
        persona_prompt=ctx["full_prompt"],
        memory_fragments=ctx["memory_ctx"].get("memory_fragments", []),
        relationship_summary=ctx["rel_summary"],
        de_ai_instructions=ctx["de_ai_instructions"],
    )
