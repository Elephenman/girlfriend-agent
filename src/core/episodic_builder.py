import logging
import uuid
from datetime import datetime

from src.core.config import Config
from src.core.graph_memory import GraphMemoryEngine
from src.core.models import SessionMemory

logger = logging.getLogger(__name__)


class EpisodicBuilder:
    """情景记忆建图器 - 从对话会话中构建知识图谱"""

    def __init__(self, config: Config, graph_engine: GraphMemoryEngine):
        self.config = config
        self.graph_engine = graph_engine
        self._entity_cache: dict[str, str] = {}  # label -> node_id 去重缓存

    def add_entity(self, entity_name: str, entity_type: str = "entity",
                   properties: dict | None = None) -> str:
        """添加实体节点，自动去重"""
        # 检查是否已存在
        existing_id = self._find_entity(entity_name)
        if existing_id:
            # 合并属性（直接读取节点数据，避免触发 get_node 的 access_count 递增）
            if properties:
                node_data = self.graph_engine.graph.nodes[existing_id]
                merged = {**node_data.get("properties", {}), **properties}
                node_data["properties"] = merged
            return existing_id

        node_id = self.graph_engine.add_node(
            node_id=f"ent_{uuid.uuid4().hex[:8]}",
            node_type=entity_type,
            label=entity_name,
            properties=properties or {},
        )
        self._entity_cache[entity_name.lower()] = node_id
        return node_id

    def add_relation(self, source_entity: str, target_entity: str,
                     relation_type: str, properties: dict | None = None) -> bool:
        """添加实体间的关系边"""
        source_id = self._find_entity(source_entity)
        target_id = self._find_entity(target_entity)

        if not source_id:
            source_id = self.add_entity(source_entity)
        if not target_id:
            target_id = self.add_entity(target_entity)

        # 检查是否已存在相同边
        if self.graph_engine.graph.has_edge(source_id, target_id):
            existing = self.graph_engine.graph.edges[source_id, target_id]
            if existing.get("relation") == relation_type:
                # 更新权重
                self.graph_engine.graph.edges[source_id, target_id]["weight"] = \
                    min(existing.get("weight", 1.0) + 0.1, 2.0)
                return True

        self.graph_engine.add_edge(
            source_id, target_id,
            relation=relation_type,
            properties=properties or {},
        )
        return True

    def add_event(self, event_desc: str, related_entities: list[str],
                  timestamp: str | None = None, emotion: str = "") -> str:
        """添加事件节点并关联到实体"""
        now = datetime.now().strftime("%Y-%m-%d")
        event_id = self.graph_engine.add_node(
            node_id=f"evt_{uuid.uuid4().hex[:8]}",
            node_type="event",
            label=event_desc,
            properties={
                "timestamp": timestamp or now,
                "emotion": emotion,
            },
        )

        # 连接事件和实体
        for entity_name in related_entities:
            entity_id = self._find_entity(entity_name)
            if not entity_id:
                entity_id = self.add_entity(entity_name)
            self.graph_engine.add_edge(
                entity_id, event_id,
                relation="about",
            )

        return event_id

    def build_causal_chain(self, event_ids: list[str]) -> None:
        """构建因果链：串联事件形成因果关系"""
        for i in range(len(event_ids) - 1):
            if (event_ids[i] in self.graph_engine.graph and
                event_ids[i + 1] in self.graph_engine.graph):
                self.graph_engine.add_edge(
                    event_ids[i], event_ids[i + 1],
                    relation="caused",
                )

    def merge_entities(self, entity_id_a: str, entity_id_b: str) -> str:
        """合并重复实体：保留ID a，将b的边迁移到a"""
        if entity_id_a not in self.graph_engine.graph:
            return entity_id_b
        if entity_id_b not in self.graph_engine.graph:
            return entity_id_a

        # 合并属性
        data_a = self.graph_engine.graph.nodes[entity_id_a]
        data_b = self.graph_engine.graph.nodes[entity_id_b]
        merged_props = {**data_b.get("properties", {}), **data_a.get("properties", {})}
        data_a["properties"] = merged_props

        # 迁移 b 的入边到 a
        for source, _, edge_data in list(self.graph_engine.graph.in_edges(entity_id_b, data=True)):
            if source != entity_id_a:
                self.graph_engine.add_edge(
                    source, entity_id_a,
                    relation=edge_data.get("relation", "related_to"),
                    properties=edge_data.get("properties", {}),
                    weight=edge_data.get("weight", 1.0),
                )

        # 迁移 b 的出边到 a
        for _, target, edge_data in list(self.graph_engine.graph.out_edges(entity_id_b, data=True)):
            if target != entity_id_a:
                self.graph_engine.add_edge(
                    entity_id_a, target,
                    relation=edge_data.get("relation", "related_to"),
                    properties=edge_data.get("properties", {}),
                    weight=edge_data.get("weight", 1.0),
                )

        # 删除旧节点
        self.graph_engine.graph.remove_node(entity_id_b)

        # 更新缓存
        label_b = data_b.get("label", "").lower()
        if label_b in self._entity_cache and self._entity_cache[label_b] == entity_id_b:
            self._entity_cache[label_b] = entity_id_a

        return entity_id_a

    def batch_build(self, sessions: list[SessionMemory]) -> dict:
        """批量建图：处理多个会话，提取实体和关系"""
        stats = {"entities_added": 0, "events_added": 0, "relations_added": 0}

        prev_event_id = None

        for session in sessions:
            # 从topics提取实体
            for topic in session.topics:
                entity_id = self.add_entity(topic, entity_type="topic")
                stats["entities_added"] += 1

            # 创建事件节点
            event_desc = f"对话: {', '.join(session.topics)}"
            event_id = self.add_event(
                event_desc=event_desc,
                related_entities=session.topics,
                timestamp=session.timestamp,
                emotion=session.emotion_summary,
            )
            stats["events_added"] += 1

            # 如果有情绪，添加情绪实体
            if session.emotion_summary:
                emotion_id = self.add_entity(
                    session.emotion_summary, entity_type="emotion",
                    properties={"type": "emotion_state"},
                )
                self.graph_engine.add_edge(event_id, emotion_id, relation="felt_during")
                stats["relations_added"] += 1

            # 构建时间线因果链
            if prev_event_id:
                self.graph_engine.add_edge(prev_event_id, event_id, relation="followed_by")
                stats["relations_added"] += 1

            prev_event_id = event_id

        # 保存图谱
        self.graph_engine.save_graph()

        return stats

    def get_entity_context(self, entity_name: str) -> dict:
        """获取实体的完整上下文"""
        entity_id = self._find_entity(entity_name)
        if not entity_id:
            return {"found": False, "entity": entity_name}

        node = self.graph_engine.get_node(entity_id)
        if not node:
            return {"found": False, "entity": entity_name}

        # 获取关联信息 (get_related returns GraphSearchResult)
        related = self.graph_engine.get_related(entity_id, max_depth=1)
        timeline = self.graph_engine.get_timeline(entity_id)

        return {
            "found": True,
            "entity": node.label,
            "type": node.node_type,
            "properties": node.properties,
            "related_nodes": [
                {"label": n.label, "type": n.node_type}
                for n in related.nodes if n.node_id != entity_id
            ],
            "timeline": timeline,
        }

    def _find_entity(self, label: str) -> str | None:
        """在缓存和图谱中查找实体（精确匹配标签）"""
        # 先查缓存
        if label.lower() in self._entity_cache:
            nid = self._entity_cache[label.lower()]
            if nid in self.graph_engine.graph:
                return nid

        # 在图谱中精确匹配（不用 _find_node_by_label 的模糊匹配）
        label_lower = label.lower()
        for nid, data in self.graph_engine.graph.nodes(data=True):
            if data.get("label", "").lower() == label_lower:
                self._entity_cache[label_lower] = nid
                return nid

        return None
