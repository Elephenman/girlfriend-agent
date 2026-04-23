# src/api/evolve_router.py
import json
import os

from fastapi import APIRouter, Request

from src.core.models import SessionMemory, RelationshipState

router = APIRouter()


@router.post("/evolve")
async def evolve(request: Request):
    app = request.app
    evolve_engine = app.state.evolve_engine
    memory_engine = app.state.memory_engine
    config = app.state.config
    relationship = app.state.relationship

    sessions = memory_engine.load_recent_sessions(count=7)

    if len(sessions) < 1:
        sessions = [SessionMemory(conversation_id="auto", interaction_type="daily_chat")]

    relationship, log_entry = evolve_engine.run_evolution_cycle(sessions, relationship)

    app.state.relationship = relationship
    with open(config.relationship_config_path, "w", encoding="utf-8") as f:
        json.dump(relationship.model_dump(), f, ensure_ascii=False, indent=2)

    return {
        "adjustments": log_entry.adjustments,
        "observation": log_entry.observation,
        "trigger": log_entry.trigger,
        "level": relationship.current_level,
        "intimacy": relationship.intimacy_points,
    }


@router.post("/evolve/revert")
async def revert_evolution(request: Request):
    """回退最近一次进化调整"""
    evolve_engine = request.app.state.evolve_engine
    result = evolve_engine.revert_last_evolution()

    if result["success"]:
        # 重新加载 relationship state
        config = request.app.state.config
        rel_path = config.relationship_config_path
        if os.path.exists(rel_path):
            with open(rel_path, encoding="utf-8") as f:
                rel_data = json.load(f)
            request.app.state.relationship = RelationshipState(**rel_data)

    return result


@router.post("/evolve/revert-to")
async def revert_to_version(request: Request):
    """回退到指定版本的进化状态"""
    body = await request.json()
    commit_hash = body.get("commit_hash", "")

    evolve_engine = request.app.state.evolve_engine
    result = evolve_engine.revert_to_version(commit_hash)

    if result["success"]:
        config = request.app.state.config
        rel_path = config.relationship_config_path
        if os.path.exists(rel_path):
            with open(rel_path, encoding="utf-8") as f:
                rel_data = json.load(f)
            request.app.state.relationship = RelationshipState(**rel_data)

    return result


@router.get("/evolve/history")
async def evolution_history(request: Request):
    """获取进化历史（仅进化相关commit）"""
    git_manager = request.app.state.git_manager
    return {"commits": git_manager.get_evolution_commits()}


@router.get("/evolve/direction")
async def evolve_direction(request: Request):
    """获取当前进化方向"""
    evolve_engine = request.app.state.evolve_engine
    relationship = request.app.state.relationship
    return evolve_engine.get_full_evolution_direction(relationship)


@router.get("/evolve/endings")
async def evolve_endings(request: Request):
    """获取所有可能结局"""
    evolve_engine = request.app.state.evolve_engine
    endings = evolve_engine._load_endings()
    return {"endings": endings, "total": len(endings)}


@router.get("/evolve/progress")
async def evolve_progress(request: Request):
    """获取进化进度（各属性进度百分比）"""
    evolve_engine = request.app.state.evolve_engine
    relationship = request.app.state.relationship
    progress = evolve_engine._calculate_progress(relationship)
    return {"progress": progress, "level": relationship.current_level}
