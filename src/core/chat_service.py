# src/core/chat_service.py
from typing import TypedDict

from src.core.models import ChatRequest, PersonaConfig, RelationshipState


class ChatContext(TypedDict):
    """Typed return for ChatService.build_context() - eliminates string-key access errors."""

    full_prompt: str
    rel_summary: str
    memory_ctx: dict
    de_ai_instructions: str


class ChatService:
    """Chat request processing - business logic separated from router.

    Two-phase processing pattern:
    - mutate_state(): Phase 1 - state mutation (called under lock)
    - build_context(): Phase 2 - pure reads (called outside lock)
    """

    def __init__(self, persona_engine, memory_engine, evolve_engine, graph_engine=None):
        self.persona_engine = persona_engine
        self.memory_engine = memory_engine
        self.evolve_engine = evolve_engine
        self.graph_engine = graph_engine

    def mutate_state(
        self, request: ChatRequest, persona: PersonaConfig, relationship: RelationshipState
    ) -> RelationshipState:
        """Phase 1: State mutation (to be called under lock).

        Updates intimacy, attributes, and checks for level-up.
        Returns the updated relationship for commit + persist.
        """
        relationship = self.evolve_engine.update_intimacy(request.interaction_type, relationship)
        relationship = self.evolve_engine.add_interaction_attributes(request.interaction_type, relationship)

        if self.evolve_engine.check_level_up(relationship):
            new_level = relationship.current_level + 1
            relationship = self.evolve_engine.process_level_up(new_level, relationship)

        return relationship

    def build_context(
        self, request: ChatRequest, persona: PersonaConfig, relationship: RelationshipState
    ) -> ChatContext:
        """Phase 2: Build prompt context (called outside lock).

        Uses committed relationship snapshot for all reads.
        Returns dict with keys: full_prompt, rel_summary, memory_ctx, de_ai_instructions.
        """
        current_persona = self.persona_engine.get_current_persona(persona, relationship)
        level_prompt = self.persona_engine.get_level_prompt(relationship.current_level, relationship)
        de_ai_instructions = self.persona_engine.get_de_ai_instructions(relationship)

        memory_ctx = self.memory_engine.get_injection_context(
            request.user_message, request.level, relationship,
            graph_engine=self.graph_engine,
        )

        full_prompt = f"{level_prompt}\n\n当前人格倾向：{current_persona.model_dump_json()}"
        rel_summary = f"等级Lv{relationship.current_level} 亲密度{relationship.intimacy_points}"

        return {
            "full_prompt": full_prompt,
            "rel_summary": rel_summary,
            "memory_ctx": memory_ctx,
            "de_ai_instructions": de_ai_instructions,
        }