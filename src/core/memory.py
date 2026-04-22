import json
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
        self._collection = None

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
        except Exception:
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

    def compute_weight(self, days: int, access_count: int) -> float:
        return math.sqrt(access_count + 1) * math.exp(-0.1 * days)

    def decay_all_weights(self) -> None:
        if self.collection.count() == 0:
            return

        all_ids = self.collection.get()["ids"]
        all_metas = self.collection.get()["metadatas"]

        for chunk_id, meta in zip(all_ids, all_metas):
            old_weight = float(meta.get("weight", "1.0"))
            new_weight = old_weight * 0.95  # 5% decay
            meta["weight"] = str(max(new_weight, 0.01))

        # Batch update
        for chunk_id, meta in zip(all_ids, all_metas):
            self.collection.update(ids=[chunk_id], metadatas=[meta])

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

        files = sorted(
            [f for f in os.listdir(sm_dir) if f.endswith(".json")],
            key=lambda f: os.path.getmtime(os.path.join(sm_dir, f)),
            reverse=True,
        )[:count]

        sessions = []
        for fname in files:
            with open(os.path.join(sm_dir, fname), encoding="utf-8") as f:
                data = json.load(f)
            sessions.append(SessionMemory(**data))
        return sessions

    def cleanup_old_sessions(self, keep: int = 10) -> None:
        sm_dir = self.config.session_memory_dir
        if not os.path.isdir(sm_dir):
            return

        files = sorted(
            [f for f in os.listdir(sm_dir) if f.endswith(".json")],
            key=lambda f: os.path.getmtime(os.path.join(sm_dir, f)),
            reverse=True,
        )

        for fname in files[keep:]:
            os.remove(os.path.join(sm_dir, fname))

    def get_injection_context(
        self, query: str, level: int, state: RelationshipState
    ) -> dict:
        level_config = Config.INJECTION_LEVELS.get(level, Config.INJECTION_LEVELS[1])
        max_memories = level_config["max_memories"]

        fragments = self.search_memories(query, n=max_memories, level=level)

        # Update access for retrieved memories
        for frag in fragments:
            self.update_memory_access(frag["id"])

        result = {
            "memory_fragments": [f["content"] for f in fragments],
            "recent_sessions": [],
        }

        if level >= 2:
            sessions = self.load_recent_sessions(count=5)
            result["recent_sessions"] = [
                {"topics": s.topics, "emotion": s.emotion_summary}
                for s in sessions
            ]
            result["relationship_summary"] = (
                f"等级Lv{state.current_level} 亲密度{state.intimacy_points}"
            )

        if level >= 3:
            result["evolution_state"] = {
                "attributes": state.attributes.model_dump(),
                "de_ai_score": state.de_ai_score.model_dump(),
            }

        return result
