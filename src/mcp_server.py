#!/usr/bin/env python3
"""MCP Server for girlfriend-agent — Model Context Protocol adapter.

Provides all girlfriend-agent engine capabilities as MCP tools,
allowing Claude Code and other MCP clients to directly invoke
persona chat, memory, evolution, and graph operations without
running a separate HTTP server.

Usage in Claude Code settings.json:
{
  "mcpServers": {
    "girlfriend-agent": {
      "command": "python",
      "args": ["-m", "src.mcp_server"]
    }
  }
}
"""
import asyncio
import json
import os
import traceback

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.core.config import Config, get_config
from src.core.persona import PersonaEngine
from src.core.memory import MemoryEngine
from src.core.evolve import EvolveEngine
from src.core.git_manager import GitManager
from src.core.graph_memory import GraphMemoryEngine
from src.core.episodic_builder import EpisodicBuilder
from src.core.state_manager import StateManager
from src.core.chat_service import ChatService

server = Server("girlfriend-agent")


def _init_engines():
    """Initialize all engine instances (same as engine_server lifespan)."""
    config = get_config()
    config.ensure_dirs()

    git_mgr = GitManager(data_dir=config.data_dir)
    git_mgr.init_repo()

    state_mgr = StateManager(config)
    persona = state_mgr.load_or_init_persona()
    relationship = state_mgr.load_or_init_relationship()

    persona_engine = PersonaEngine(config)
    memory_engine = MemoryEngine(config)
    evolve_engine = EvolveEngine(config, git_mgr)
    graph_engine = GraphMemoryEngine(config)
    episodic_builder = EpisodicBuilder(config, graph_engine)

    return {
        "config": config,
        "persona": persona,
        "relationship": relationship,
        "persona_engine": persona_engine,
        "memory_engine": memory_engine,
        "evolve_engine": evolve_engine,
        "git_manager": git_mgr,
        "state_manager": state_mgr,
        "graph_engine": graph_engine,
        "episodic_builder": episodic_builder,
    }


_engines = None


def _get_engines():
    global _engines
    if _engines is None:
        _engines = _init_engines()
    return _engines


def _json_result(data) -> list[TextContent]:
    """Convert any data to MCP TextContent with JSON formatting."""
    return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, default=str))]


def _error_result(msg: str) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps({"error": msg}, ensure_ascii=False))]


# ── Tool definitions ──────────────────────────────────────────────────────────

TOOLS = [
    # ── Chat ──
    Tool(
        name="chat",
        description="Process a user message through the girlfriend-agent personality engine. Updates intimacy/attributes based on interaction type, injects persona prompt + memory context + de-AI instructions. Returns a complete prompt that should be fed into your LLM for character-driven response generation.",
        inputSchema={
            "type": "object",
            "properties": {
                "user_message": {"type": "string", "description": "The user's message to the character"},
                "level": {"type": "integer", "description": "Injection level (1=basic ~600chars, 2=deep ~2500chars with graph, 3=full ~5000chars)", "enum": [1, 2, 3]},
                "interaction_type": {"type": "string", "description": "Type of interaction affecting intimacy gain", "enum": ["daily_chat", "deep_conversation", "collaborative_task", "emotion_companion", "light_chat"]},
            },
            "required": ["user_message"],
        },
    ),
    # ── Status ──
    Tool(
        name="status",
        description="Get current relationship state: level, intimacy points, all 8 attributes (care/understanding/expression/memory/humor/intuition/courage/sensitivity), de-AI scores, nickname, conflict mode.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="health",
        description="Check engine health status and whether the embedding model is loaded.",
        inputSchema={"type": "object", "properties": {}},
    ),
    # ── Persona ──
    Tool(
        name="persona_get",
        description="Get current persona configuration including personality dimensions (warmth/rationality/independence/humor/patience/curiosity/expressiveness), speech style, likes, and dislikes.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="persona_update",
        description="Update a specific persona field. Pre-validates before mutation — invalid values are rejected without corrupting state. Supports dot-path notation (e.g. 'personality_base.warmth'). Commits change to git.",
        inputSchema={
            "type": "object",
            "properties": {
                "field": {"type": "string", "description": "Field path to update (e.g. 'personality_base.warmth', 'nickname')"},
                "value": {"type": "string", "description": "New value for the field (strings for text, numbers as strings for numeric fields)"},
            },
            "required": ["field", "value"],
        },
    ),
    Tool(
        name="persona_apply_template",
        description="Apply a preset persona template. Available: default, tsundere, gentle, lively, intellectual, little_sister, custom_skeleton. Resets personality dimensions to template values and commits to git.",
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {"type": "string", "description": "Template to apply", "enum": ["default", "tsundere", "gentle", "lively", "intellectual", "little_sister", "custom_skeleton"]},
            },
            "required": ["template_id"],
        },
    ),
    # ── Memory (Vector) ──
    Tool(
        name="memory_update",
        description="Store a new memory fragment in the long-term vector store. Memories are semantically searchable and decay over time following Ebbinghaus forgetting curve.",
        inputSchema={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The memory content to store"},
                "memory_type": {"type": "string", "description": "Type of memory", "enum": ["fact", "preference", "event", "emotion"]},
            },
            "required": ["content"],
        },
    ),
    Tool(
        name="memory_search",
        description="Search long-term memories by semantic similarity. Returns top-k matching fragments with their weights and metadata.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "level": {"type": "integer", "description": "Injection level context (1-3)", "enum": [1, 2, 3]},
                "n": {"type": "integer", "description": "Number of results to return (default 5)"},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="memory_reinforce",
        description="Strengthen a specific memory's weight to prevent it from decaying. Use after a memory is referenced in conversation to reinforce recall.",
        inputSchema={
            "type": "object",
            "properties": {
                "chunk_id": {"type": "string", "description": "The memory chunk ID to reinforce"},
                "strength": {"type": "number", "description": "Reinforcement strength (0.0-1.0, default 0.1)"},
            },
            "required": ["chunk_id"],
        },
    ),
    Tool(
        name="memory_decay",
        description="Execute memory decay on both vector memories and graph nodes. Reduces weights over time following the forgetting curve. Should be called periodically.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="memory_emotion_trend",
        description="Analyze emotional patterns from recent conversation sessions. Returns positive/negative trend data over time.",
        inputSchema={
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "Number of recent sessions to analyze (1-50, default 10)"},
            },
        },
    ),
    # ── Memory (Graph / Episodic) ──
    Tool(
        name="graph_add_entity",
        description="Add an entity node to the episodic knowledge graph. Idempotent — if entity already exists, merges properties and returns existing node_id with created=false.",
        inputSchema={
            "type": "object",
            "properties": {
                "entity_name": {"type": "string", "description": "Name of the entity (e.g. '猫咪', '旅行')"},
                "entity_type": {"type": "string", "description": "Type of entity", "enum": ["entity", "event", "topic", "emotion"]},
            },
            "required": ["entity_name"],
        },
    ),
    Tool(
        name="graph_add_relation",
        description="Add a relation edge between two entities. Idempotent — if relation already exists, strengthens weight instead of creating duplicate.",
        inputSchema={
            "type": "object",
            "properties": {
                "source_entity": {"type": "string", "description": "Source entity name"},
                "target_entity": {"type": "string", "description": "Target entity name"},
                "relation_type": {"type": "string", "description": "Type of relation", "enum": ["caused", "related_to", "followed_by", "about", "felt_during"]},
            },
            "required": ["source_entity", "target_entity"],
        },
    ),
    Tool(
        name="graph_add_event",
        description="Add an episodic event to the knowledge graph with optional associated entities and emotion tag.",
        inputSchema={
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Event description"},
                "entities": {"type": "array", "items": {"type": "string"}, "description": "Entity names associated with this event"},
                "emotion": {"type": "string", "description": "Emotion tag for the event"},
            },
            "required": ["description"],
        },
    ),
    Tool(
        name="graph_search",
        description="Search the episodic knowledge graph using BFS with inverted index optimization. Returns matching nodes, edges, and a context summary.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (entity name or keyword)"},
                "max_depth": {"type": "integer", "description": "BFS traversal depth (1-10, default 3)"},
                "max_nodes": {"type": "integer", "description": "Max nodes to return (1-100, default 20)"},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="graph_timeline",
        description="Get the chronological timeline of events related to a specific entity in the knowledge graph.",
        inputSchema={
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "Entity node ID to get timeline for"},
            },
            "required": ["entity_id"],
        },
    ),
    Tool(
        name="graph_batch_build",
        description="Batch build episodic graph from recent conversation sessions. Extracts entities and relations from session data.",
        inputSchema={
            "type": "object",
            "properties": {
                "session_count": {"type": "integer", "description": "Number of recent sessions to process (1-30, default 7)"},
            },
        },
    ),
    Tool(
        name="graph_stats",
        description="Get knowledge graph statistics: node counts by type, edge counts, graph density.",
        inputSchema={"type": "object", "properties": {}},
    ),
    # ── Evolution ──
    Tool(
        name="evolve_run",
        description="Run an evolution cycle: analyze recent sessions for patterns (topics, emotions, hidden needs), micro-adjust personality dimensions (≤10% per step), process level-up if threshold reached, git commit. Trigger every 7 conversations.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="evolve_direction",
        description="Get current evolution direction — which ending trajectory the relationship is heading toward based on accumulated attribute changes.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="evolve_endings",
        description="List all 56 possible evolution endings (8 attributes × 7 secondary dimensions). Each ending represents a unique relationship trajectory.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="evolve_progress",
        description="Get evolution progress for each attribute (0.0-1.0 scale) showing how far along each dimension has evolved.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="evolve_history",
        description="Get git commit history of all evolution adjustments. Each commit records personality changes made during that evolution cycle.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="evolve_revert",
        description="Revert the most recent evolution adjustment. Restores personality and relationship state to the previous git commit.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="evolve_revert_to",
        description="Revert to a specific evolution version by git commit hash. Restores all state (persona + relationship) to that point in history.",
        inputSchema={
            "type": "object",
            "properties": {
                "commit_hash": {"type": "string", "description": "Git commit hash to revert to (7-40 hex characters)"},
            },
            "required": ["commit_hash"],
        },
    ),
    # ── Rollback ──
    Tool(
        name="rollback",
        description="Full state rollback — revert both persona and relationship to a specific git commit. More comprehensive than evolve_revert which only rolls back evolution adjustments.",
        inputSchema={
            "type": "object",
            "properties": {
                "commit_hash": {"type": "string", "description": "Git commit hash to rollback to"},
            },
            "required": ["commit_hash"],
        },
    ),
]


@server.list_tools()
async def list_tools():
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        e = _get_engines()
        config = e["config"]

        # ── Chat ──
        if name == "chat":
            chat_service = ChatService(
                persona_engine=e["persona_engine"],
                memory_engine=e["memory_engine"],
                evolve_engine=e["evolve_engine"],
                graph_engine=e["graph_engine"],
            )
            from src.core.models import ChatRequest
            req = ChatRequest(
                user_message=arguments["user_message"],
                level=arguments.get("level", 1),
                interaction_type=arguments.get("interaction_type", "daily_chat"),
            )
            relationship = chat_service.mutate_state(req, e["persona"], e["relationship"])
            e["relationship"] = relationship
            e["state_manager"].save_relationship(e["relationship"])
            ctx = chat_service.build_context(req, e["persona"], relationship)
            return _json_result({
                "persona_prompt": ctx["full_prompt"],
                "memory_fragments": ctx["memory_ctx"].get("memory_fragments", []),
                "relationship_summary": ctx["rel_summary"],
                "de_ai_instructions": ctx["de_ai_instructions"],
            })

        # ── Status ──
        if name == "status":
            rel = e["relationship"]
            return _json_result({
                "current_level": rel.current_level,
                "intimacy_points": rel.intimacy_points,
                "nickname": rel.nickname,
                "conflict_mode": rel.conflict_mode,
                "attributes": rel.attributes.model_dump() if hasattr(rel.attributes, "model_dump") else rel.attributes,
                "de_ai_score": rel.de_ai_score.model_dump(),
            })

        if name == "health":
            return _json_result({
                "status": "ok",
                "embedding_loaded": e["memory_engine"].client is not None,
            })

        # ── Persona ──
        if name == "persona_get":
            return _json_result(e["persona"].model_dump())

        if name == "persona_update":
            result = e["persona_engine"].update_persona_field(
                e["persona"], arguments["field"], arguments["value"]
            )
            e["state_manager"].save_persona(e["persona"])
            e["git_manager"].commit("persona update: " + arguments["field"])
            return _json_result({"status": "ok", "field": arguments["field"], "validated": True})

        if name == "persona_apply_template":
            from src.core.persona import PersonaConfig
            template_id = arguments["template_id"]
            template_path = os.path.join(config.templates_dir, f"{template_id}.json")
            if not os.path.isfile(template_path):
                return _error_result(f"Template '{template_id}' not found")
            with open(template_path, "r", encoding="utf-8") as f:
                template_data = json.load(f)
            e["persona"] = PersonaConfig.model_validate(template_data)
            e["state_manager"].save_persona(e["persona"])
            e["git_manager"].commit(f"apply template: {template_id}")
            return _json_result({"status": "ok", "template": template_id, "persona": e["persona"].model_dump()})

        # ── Memory (Vector) ──
        if name == "memory_update":
            chunk_id = e["memory_engine"].store_memory(
                arguments["content"],
                arguments.get("memory_type", "fact"),
            )
            return _json_result({"status": "ok", "chunk_id": chunk_id})

        if name == "memory_search":
            results = e["memory_engine"].search_memories(
                arguments["query"],
                n=arguments.get("n", 5),
                level=arguments.get("level", 1),
            )
            return _json_result({"results": results})

        if name == "memory_reinforce":
            e["memory_engine"].reinforce_memory(
                arguments["chunk_id"],
                arguments.get("strength", 0.1),
            )
            return _json_result({"status": "ok"})

        if name == "memory_decay":
            e["memory_engine"].decay_all_weights()
            e["graph_engine"].decay_graph_weights()
            e["graph_engine"].save_graph()
            return _json_result({"status": "ok"})

        if name == "memory_emotion_trend":
            sessions = e["memory_engine"].load_recent_sessions(count=arguments.get("count", 10))
            trend = e["memory_engine"].compute_emotion_trend(sessions)
            return _json_result(trend)

        # ── Memory (Graph) ──
        if name == "graph_add_entity":
            builder = e["episodic_builder"]
            existing_id = builder._find_entity(arguments["entity_name"])
            node_id = builder.add_entity(
                arguments["entity_name"],
                arguments.get("entity_type", "entity"),
            )
            e["graph_engine"].save_graph()
            return _json_result({"status": "ok", "node_id": node_id, "created": not existing_id})

        if name == "graph_add_relation":
            builder = e["episodic_builder"]
            success = builder.add_relation(
                arguments["source_entity"],
                arguments["target_entity"],
                arguments.get("relation_type", "related_to"),
            )
            e["graph_engine"].save_graph()
            return _json_result({"status": "ok" if success else "error"})

        if name == "graph_add_event":
            builder = e["episodic_builder"]
            event_id = builder.add_event(
                arguments["description"],
                arguments.get("entities", []),
                arguments.get("timestamp"),
                arguments.get("emotion", ""),
            )
            e["graph_engine"].save_graph()
            return _json_result({"status": "ok", "event_id": event_id})

        if name == "graph_search":
            result = e["graph_engine"].search_graph(
                arguments["query"],
                arguments.get("max_depth", 3),
                arguments.get("max_nodes", 20),
            )
            return _json_result(result.model_dump())

        if name == "graph_timeline":
            timeline = e["graph_engine"].get_timeline(arguments["entity_id"])
            return _json_result({"timeline": timeline})

        if name == "graph_batch_build":
            sessions = e["memory_engine"].load_recent_sessions(count=arguments.get("session_count", 7))
            stats = e["episodic_builder"].batch_build(sessions)
            return _json_result({"status": "ok", "stats": stats})

        if name == "graph_stats":
            return _json_result(e["graph_engine"].get_stats())

        # ── Evolution ──
        if name == "evolve_run":
            result = e["evolve_engine"].run_evolution_cycle(
                e["persona"], e["relationship"]
            )
            e["state_manager"].save_relationship(e["relationship"])
            return _json_result(result)

        if name == "evolve_direction":
            direction = e["evolve_engine"].get_evolution_direction(e["persona"], e["relationship"])
            return _json_result(direction)

        if name == "evolve_endings":
            from src.core.evolve import ENDINGS_LIBRARY
            return _json_result({"endings": ENDINGS_LIBRARY, "total": len(ENDINGS_LIBRARY)})

        if name == "evolve_progress":
            progress = e["evolve_engine"].get_attribute_progress(e["relationship"])
            return _json_result({"progress": progress, "level": e["relationship"].current_level})

        if name == "evolve_history":
            commits = e["git_manager"].get_evolution_commits()
            return _json_result({"commits": commits})

        if name == "evolve_revert":
            result = e["evolve_engine"].revert_to_version(e["persona"], e["relationship"], "HEAD~1")
            if result.get("success"):
                e["persona"] = e["state_manager"].load_persona(config)
                e["relationship"] = e["state_manager"].load_relationship(config)
            return _json_result(result)

        if name == "evolve_revert_to":
            result = e["evolve_engine"].revert_to_version(
                e["persona"], e["relationship"], arguments["commit_hash"]
            )
            if result.get("success"):
                e["persona"] = e["state_manager"].load_persona(config)
                e["relationship"] = e["state_manager"].load_relationship(config)
            return _json_result(result)

        # ── Rollback ──
        if name == "rollback":
            commit_hash = arguments["commit_hash"]
            e["git_manager"].checkout(commit_hash)
            e["persona"] = e["state_manager"].load_persona(config)
            e["relationship"] = e["state_manager"].load_relationship(config)
            return _json_result({"status": "ok", "commit_hash": commit_hash})

        return _error_result(f"Unknown tool: {name}")

    except Exception as exc:
        return _error_result(f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}")


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run_async(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())