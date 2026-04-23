import json
import logging
import math
import os
import uuid
from datetime import datetime

import chromadb

from src.core.config import Config
from src.core.models import RelationshipState, SessionMemory


class MemoryEngine:
    def __init__(self, config: Config):
        self.config = config
        self._client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None

    @property
    def client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self._client = chromadb.PersistentClient(path=self.config.chroma_db_dir)
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name="girlfriend_memories",
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def store_memory(self, content: str, memory_type: str, metadata: dict | None = None) -> str:
        chunk_id = str(uuid.uuid4())
        weight = self.compute_weight(days=0, access_count=0)
        meta = {
            "memory_type": memory_type,
            "weight": str(weight),
            "access_count": "0",
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "last_accessed": datetime.now().strftime("%Y-%m-%d"),
        }
        if metadata:
            for k, v in metadata.items():
                meta[f"user_{k}"] = str(v)

        self.collection.add(
            ids=[chunk_id],
            documents=[content],
            metadatas=[meta],
        )
        return chunk_id

    def search_memories(self, query: str, n: int = 5, level: int = 1) -> list[dict]:
        fetch_n = n * 2
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=min(fetch_n, self.collection.count()),
        )

        if not results["documents"] or not results["documents"][0]:
            return []

        fragments = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            weight = float(meta.get("weight", "1.0"))
            # Filter by weight threshold based on level
            min_weight = {1: 0.3, 2: 0.1, 3: 0.0}.get(level, 0.3)
            if weight >= min_weight:
                fragments.append({
                    "content": doc,
                    "weight": weight,
                    "memory_type": meta.get("memory_type", "fact"),
                    "id": results["ids"][0][i],
                })

        fragments.sort(key=lambda x: x["weight"], reverse=True)
        return fragments[:n]

    def update_memory_access(self, chunk_id: str) -> None:
        try:
            result = self.collection.get(ids=[chunk_id])
        except Exception as e:
            logging.warning("Failed to get memory chunk %s: %s", chunk_id, e)
            return
        if not result["metadatas"]:
            return

        meta = result["metadatas"][0]
        access_count = int(meta.get("access_count", "0")) + 1
        old_weight = float(meta.get("weight", "1.0"))
        created = meta.get("created_date", datetime.now().strftime("%Y-%m-%d"))

        days = (datetime.now() - datetime.strptime(created, "%Y-%m-%d")).days
        new_weight = self.compute_weight(days=days, access_count=access_count)

        meta["access_count"] = str(access_count)
        meta["weight"] = str(new_weight)
        meta["last_accessed"] = datetime.now().strftime("%Y-%m-%d")

        self.collection.update(
            ids=[chunk_id],
            metadatas=[meta],
        )

    def reinforce_memory(self, chunk_id: str, strength: float = 0.1) -> None:
        """强化单条记忆的权重"""
        try:
            result = self.collection.get(ids=[chunk_id])
        except Exception as e:
            logging.warning("Failed to get memory chunk %s: %s", chunk_id, e)
            return
        if not result["metadatas"]:
            return

        meta = result["metadatas"][0]
        old_weight = float(meta.get("weight", "1.0"))
        new_weight = min(old_weight + strength, 2.0)  # 上限 2.0
        meta["weight"] = str(new_weight)
        meta["last_accessed"] = datetime.now().strftime("%Y-%m-%d")

        self.collection.update(ids=[chunk_id], metadatas=[meta])

    def reinforce_path(self, path_node_ids: list[str], strength: float = 0.1) -> None:
        """强化路径上所有记忆节点"""
        for chunk_id in path_node_ids:
            self.reinforce_memory(chunk_id, strength)

    def compute_weight(self, days: int, access_count: int,
                       decay_lambda: float | None = None) -> float:
        """艾宾浩斯遗忘曲线简化版
        - days: 距离上次访问的天数
        - access_count: 被检索次数
        - decay_lambda: 衰减速率，默认使用配置值
        """
        if decay_lambda is None:
            decay_lambda = self.config.WEIGHT_DECAY_LAMBDA
        return math.sqrt(access_count + 1) * math.exp(-decay_lambda * days)

    def decay_all_weights(self) -> None:
        """基于真实天数的精确衰减（预验证 + 批量更新 + 错误容忍）"""
        if self.collection.count() == 0:
            return

        all_data = self.collection.get()
        all_ids = all_data["ids"]
        all_metas = all_data["metadatas"]
        now = datetime.now()

        # Pre-validate metadata before batch update
        valid_ids = []
        valid_metas = []
        skipped = 0

        for i, (chunk_id, meta) in enumerate(zip(all_ids, all_metas)):
            created = meta.get("created_date", now.strftime("%Y-%m-%d"))
            try:
                days = (now - datetime.strptime(created, "%Y-%m-%d")).days
            except ValueError:
                days = 0

            access_count = int(meta.get("access_count", "0"))
            new_weight = self.compute_weight(days=days, access_count=access_count)
            meta["weight"] = str(max(new_weight, 0.01))

            # Validate metadata fields are well-formed
            try:
                float(meta["weight"])
                int(meta.get("access_count", "0"))
                valid_ids.append(chunk_id)
                valid_metas.append(meta)
            except (ValueError, TypeError, KeyError) as e:
                skipped += 1
                logging.warning(
                    "Skipping invalid metadata for chunk %s: %s", chunk_id, e
                )

        if skipped:
            logging.warning("decay_all_weights: skipped %d invalid chunks out of %d", skipped, len(all_ids))

        if not valid_ids:
            return

        # Try batch update first; fall back to per-item updates on failure
        try:
            self.collection.update(ids=valid_ids, metadatas=valid_metas)
        except Exception as e:
            logging.warning("Batch decay update failed (%s), falling back to per-item updates", e)
            for chunk_id, meta in zip(valid_ids, valid_metas):
                try:
                    self.collection.update(ids=[chunk_id], metadatas=[meta])
                except Exception as item_err:
                    logging.warning("Failed to decay chunk %s: %s", chunk_id, item_err)

    def save_session(self, session: SessionMemory) -> None:
        path = os.path.join(
            self.config.session_memory_dir,
            f"{session.conversation_id}.json",
        )
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session.model_dump(), f, ensure_ascii=False, indent=2)

    def load_recent_sessions(self, count: int = 10) -> list[SessionMemory]:
        sm_dir = self.config.session_memory_dir
        if not os.path.isdir(sm_dir):
            return []

        # Safety: limit number of files scanned to prevent memory/time blow-up
        json_files = [f for f in os.listdir(sm_dir) if f.endswith(".json")]
        max_files = self.config.max_session_files  # Configurable via Config

        if len(json_files) > max_files:
            logging.warning(
                "Session directory has %d files (limit %d). Pre-filtering by mtime.",
                len(json_files), max_files,
            )
            # Sort by file modification time as fallback (more reliable than filename)
            json_files_with_mtime = [
                (f, os.path.getmtime(os.path.join(sm_dir, f)))
                for f in json_files
            ]
            json_files_with_mtime.sort(key=lambda x: x[1], reverse=True)
            json_files = [f for f, _ in json_files_with_mtime[:max_files]]

        sessions = []
        for fname in json_files:
            fpath = os.path.join(sm_dir, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append(SessionMemory(**data))
            except (json.JSONDecodeError, Exception) as e:
                logging.warning("Skipping corrupt session file %s: %s", fname, e)
                continue

        # Sort by session timestamp, not file modification time
        sessions.sort(key=lambda s: s.timestamp, reverse=True)
        return sessions[:count]

    def cleanup_old_sessions(self, keep: int = 10) -> None:
        sm_dir = self.config.session_memory_dir
        if not os.path.isdir(sm_dir):
            return

        try:
            sessions = []
            for fname in os.listdir(sm_dir):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(sm_dir, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        data = json.load(f)
                    session = SessionMemory(**data)
                    sessions.append((session.timestamp, fname))
                except (json.JSONDecodeError, Exception):
                    # Corrupt file - remove it
                    try:
                        os.remove(fpath)
                    except OSError:
                        pass

            # Sort by session timestamp, consistent with load_recent_sessions
            sessions.sort(key=lambda x: x[0], reverse=True)

            # Remove files beyond the keep limit
            for _, fname in sessions[keep:]:
                try:
                    os.remove(os.path.join(sm_dir, fname))
                except OSError:
                    pass
        except Exception as e:
            logging.warning("Failed to cleanup old sessions: %s", e)

    def compute_emotion_trend(self, sessions: list[SessionMemory]) -> dict:
        """从会话历史中计算情绪变化趋势"""
        if not sessions:
            return {"trend": "neutral", "recent_emotions": [], "summary": ""}

        emotions = [s.emotion_summary for s in sessions if s.emotion_summary]
        if not emotions:
            return {"trend": "neutral", "recent_emotions": [], "summary": ""}

        # 简单情绪分类
        positive_keywords = Config.POSITIVE_KEYWORDS
        negative_keywords = Config.NEGATIVE_KEYWORDS

        recent = emotions[-5:]  # 最近5次
        pos_count = sum(1 for e in recent if any(k in e for k in positive_keywords))
        neg_count = sum(1 for e in recent if any(k in e for k in negative_keywords))

        if pos_count > neg_count:
            trend = "improving"
        elif neg_count > pos_count:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "recent_emotions": recent,
            "summary": f"近期情绪趋势：{trend}（正面{pos_count}次，负面{neg_count}次）",
        }

    def get_injection_context(
        self, query: str, level: int, state: RelationshipState,
        graph_engine=None,
    ) -> dict:
        """渐进式记忆注入 - Level 1/2/3 完整实现"""
        level_config = Config.INJECTION_LEVELS.get(level, Config.INJECTION_LEVELS[1])
        max_memories = level_config["max_memories"]

        # --- 基础记忆检索 (所有级别) ---
        fragments = self.search_memories(query, n=max_memories, level=level)
        for frag in fragments:
            self.update_memory_access(frag["id"])
            self.reinforce_memory(frag["id"], strength=Config.REINFORCE_STRENGTH_HIT)

        result = {
            "memory_fragments": [f["content"] for f in fragments],
            "recent_sessions": [],
        }

        # --- Level 1: 3条记忆 + persona摘要 (~600字) ---
        if level >= 1:
            result["persona_summary"] = (
                f"关系等级Lv{state.current_level}，亲密度{state.intimacy_points}"
            )

        # --- Level 2: + 8条记忆 + 关系状态 + 近期情绪趋势 + 图谱关联 (~2500字) ---
        if level >= 2:
            try:
                sessions = self.load_recent_sessions(count=5)
                result["recent_sessions"] = [
                    {"topics": s.topics, "emotion": s.emotion_summary}
                    for s in sessions
                ]
                result["relationship_summary"] = (
                    f"等级Lv{state.current_level} 亲密度{state.intimacy_points} "
                    f"昵称:{state.nickname or '未设定'} "
                    f"共同话题:{','.join(state.shared_jokes[:3]) if state.shared_jokes else '无'}"
                )
                result["emotion_trend"] = self.compute_emotion_trend(sessions)
            except Exception as e:
                logging.warning("Failed to load Level 2 context: %s", e)
                result["recent_sessions"] = []
                result["relationship_summary"] = (
                    f"等级Lv{state.current_level} 亲密度{state.intimacy_points}"
                )
                result["emotion_trend"] = {"trend": "neutral", "recent_emotions": [], "summary": ""}

            # 图谱关联（如果 graph_engine 可用）
            if graph_engine is not None:
                try:
                    graph_result = graph_engine.search_graph(
                        query, max_depth=1, max_nodes=5
                    )
                    result["graph_context"] = graph_result.context_summary
                except Exception as e:
                    logging.warning("Graph search failed: %s", e)
                    result["graph_context"] = ""

        # --- Level 3: + 15条记忆 + 完整进化状态 + 图谱遍历 + 原始对话 (~5000字) ---
        if level >= 3:
            result["evolution_state"] = {
                "attributes": state.attributes.model_dump(),
                "de_ai_score": state.de_ai_score.model_dump(),
                "conflict_mode": state.conflict_mode,
            }

            # 完整图谱遍历
            if graph_engine is not None:
                try:
                    graph_result = graph_engine.search_graph(
                        query, max_depth=3, max_nodes=15
                    )
                    result["graph_full"] = {
                        "nodes": [
                            {"id": n.node_id, "label": n.label, "type": n.node_type}
                            for n in graph_result.nodes
                        ],
                        "edges": [
                            {"from": e.source_id, "to": e.target_id, "relation": e.relation}
                            for e in graph_result.edges
                        ],
                        "summary": graph_result.context_summary,
                    }
                    # 强化图谱路径
                    path_ids = [n.node_id for n in graph_result.nodes]
                    graph_engine.reinforce_path(path_ids)
                except Exception as e:
                    logging.warning("Full graph search failed: %s", e)
                    result["graph_full"] = {}

            # 原始对话记录
            try:
                recent_sessions = self.load_recent_sessions(count=3)
                result["raw_sessions"] = [
                    {
                        "id": s.conversation_id,
                        "topics": s.topics,
                        "emotion": s.emotion_summary,
                        "type": s.interaction_type,
                        "timestamp": s.timestamp,
                    }
                    for s in recent_sessions
                ]
            except Exception as e:
                logging.warning("Failed to load raw sessions: %s", e)
                result["raw_sessions"] = []

        return result

    def estimate_char_count(self, context: dict) -> int:
        """估算注入上下文的字符数"""
        total = 0
        for key, value in context.items():
            if isinstance(value, str):
                total += len(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        total += len(item)
                    elif isinstance(item, dict):
                        for v in item.values():
                            if isinstance(v, str):
                                total += len(v)
            elif isinstance(value, dict):
                for v in value.values():
                    if isinstance(v, str):
                        total += len(v)
        return total

    def trim_to_budget(self, context: dict, target_chars: int) -> dict:
        """按字数预算裁剪注入内容"""
        current = self.estimate_char_count(context)
        if current <= target_chars:
            return context

        # 按优先级裁剪：先裁剪 raw_sessions，再裁剪 graph_full，再裁剪 memory_fragments
        trimmed = dict(context)

        # 裁剪原始对话
        if "raw_sessions" in trimmed and len(trimmed["raw_sessions"]) > 1:
            trimmed["raw_sessions"] = trimmed["raw_sessions"][:1]

        current = self.estimate_char_count(trimmed)
        if current <= target_chars:
            return trimmed

        # 裁剪图谱详情
        if "graph_full" in trimmed:
            del trimmed["graph_full"]

        current = self.estimate_char_count(trimmed)
        if current <= target_chars:
            return trimmed

        # 裁剪记忆片段
        if "memory_fragments" in trimmed:
            while self.estimate_char_count(trimmed) > target_chars and len(trimmed["memory_fragments"]) > 1:
                trimmed["memory_fragments"] = trimmed["memory_fragments"][:-1]

        return trimmed
