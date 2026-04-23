# src/api/chat_router.py
from fastapi import APIRouter, Request

from src.core.models import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    app = request.app
    persona_engine = app.state.persona_engine
    memory_engine = app.state.memory_engine
    evolve_engine = app.state.evolve_engine

    persona = app.state.persona
    relationship = app.state.relationship

    # Update intimacy and attributes
    relationship = evolve_engine.update_intimacy(req.interaction_type, relationship)
    relationship = evolve_engine.add_interaction_attributes(req.interaction_type, relationship)

    # Check level up
    if evolve_engine.check_level_up(relationship):
        new_level = relationship.current_level + 1
        relationship = evolve_engine.process_level_up(new_level, relationship)

    # Get persona prompt
    current_persona = persona_engine.get_current_persona(persona, relationship)
    level_prompt = persona_engine.get_level_prompt(relationship.current_level, relationship)

    # Get de-AI instructions
    de_ai_instructions = persona_engine.get_de_ai_instructions(relationship)

    # Get memory injection
    graph_engine = getattr(request.app.state, "graph_engine", None)
    memory_ctx = memory_engine.get_injection_context(
        req.user_message, req.level, relationship, graph_engine=graph_engine
    )

    # Build full prompt
    full_prompt = f"{level_prompt}\n\n当前人格倾向：{current_persona.model_dump_json()}"
    rel_summary = f"等级Lv{relationship.current_level} 亲密度{relationship.intimacy_points}"

    # Save updated state
    app.state.relationship = relationship
    app.state.state_manager.persist_relationship(app)

    return ChatResponse(
        persona_prompt=full_prompt,
        memory_fragments=memory_ctx.get("memory_fragments", []),
        relationship_summary=rel_summary,
        de_ai_instructions=de_ai_instructions,
    )
