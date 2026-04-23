import json
import logging
import math
import os
import uuid
from collections import deque
from datetime import datetime

import networkx as nx

from src.core.config import Config
from src.core.models import GraphNode, GraphEdge, GraphSearchResult

logger = logging.getLogger(__name__)


class GraphMemoryEngine:
    """基于 NetworkX 的情景记忆图谱引擎"""

    def __init__(self, config: Config):
        self.config = config
        self._graph: nx.DiGraph | None = None

    @property
    def graph(self) -> nx.DiGraph:
        if self._graph is None:
            self._graph = self.load_graph()
        return self._graph

    def add_node(
        self,
        node_id: str | None,
        node_type: str,
        label: str,
        properties: dict | None = None,
        weight: float = 1.0,
    ) -> str:
        """添加节点，返回node_id"""
        if node_id is None:
            node_id = f"node_{uuid.uuid4().hex[:8]}"
        now = datetime.now().strftime("%Y-%m-%d")
        self.graph.add_node(
            node_id,
            node_type=node_type,
            label=label,
            properties=properties or {},
            weight=weight,
            created_date=now,
            last_accessed=now,
            access_count=0,
        )
        return node_id

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        properties: dict | None = None,
        weight: float = 1.0,
    ) -> None:
        """添加边"""
        now = datetime.now().strftime("%Y-%m-%d")
        self.graph.add_edge(
            source_id,
            target_id,
            relation=relation,
            properties=properties or {},
            weight=weight,
            created_date=now,
        )

    def get_node_info(self, node_id: str) -> GraphNode | None:
        """获取节点信息（纯查询，无副作用）"""
        if node_id not in self.graph:
            return None
        data = self.graph.nodes[node_id]
        now = datetime.now().strftime("%Y-%m-%d")
        return GraphNode(
            node_id=node_id,
            node_type=data.get("node_type", "entity"),
            label=data.get("label", ""),
            properties=data.get("properties", {}),
            weight=data.get("weight", 1.0),
            created_date=data.get("created_date", now),
            last_accessed=data.get("last_accessed", now),
            access_count=data.get("access_count", 0),
        )

    def touch_node(self, node_id: str) -> None:
        """更新节点访问计数和最后访问时间（副作用操作）"""
        if node_id not in self.graph:
            return
        data = self.graph.nodes[node_id]
        data["access_count"] = data.get("access_count", 0) + 1
        data["last_accessed"] = datetime.now().strftime("%Y-%m-%d")

    def get_node(self, node_id: str, touch: bool = True) -> GraphNode | None:
        """获取节点信息，可选更新访问计数（向后兼容接口）

        Args:
            node_id: Node identifier.
            touch: If True, update access_count and last_accessed (original behavior).
                   If False, pure query without side effects.

        Default touch=True maintains backward compatibility with original get_node behavior.
        """
        result = self.get_node_info(node_id)
        if result is not None and touch:
            self.touch_node(node_id)
            result = self.get_node_info(node_id)  # re-read to reflect updated values
        return result

    def search_graph(
        self, query: str, max_depth: int = 3, max_nodes: int = 20
    ) -> GraphSearchResult:
        """从匹配标签的种子节点出发进行BFS遍历"""
        # 1. 找种子节点（标签包含query的节点）
        seed_nodes: list[str] = []
        query_lower = query.lower()
        for nid, data in self.graph.nodes(data=True):
            if query_lower in data.get("label", "").lower():
                seed_nodes.append(nid)
            elif query_lower in str(data.get("properties", {})).lower():
                seed_nodes.append(nid)

        if not seed_nodes:
            return GraphSearchResult(
                nodes=[], edges=[], context_summary="未找到相关图谱节点"
            )

        # 2. BFS遍历
        visited_nodes: set[str] = set()
        visited_edges: list[GraphEdge] = []
        queue: deque[tuple[str, int]] = deque((n, 0) for n in seed_nodes)

        while queue and len(visited_nodes) < max_nodes:
            node_id, depth = queue.popleft()
            if node_id in visited_nodes or depth > max_depth:
                continue
            visited_nodes.add(node_id)

            for _, target, edge_data in self.graph.out_edges(node_id, data=True):
                if len(visited_nodes) < max_nodes:
                    visited_edges.append(
                        GraphEdge(
                            source_id=node_id,
                            target_id=target,
                            relation=edge_data.get("relation", "related_to"),
                            properties=edge_data.get("properties", {}),
                            weight=edge_data.get("weight", 1.0),
                            created_date=edge_data.get("created_date", ""),
                        )
                    )
                    if target not in visited_nodes:
                        queue.append((target, depth + 1))

            for source, _, edge_data in self.graph.in_edges(node_id, data=True):
                if len(visited_nodes) < max_nodes:
                    visited_edges.append(
                        GraphEdge(
                            source_id=source,
                            target_id=node_id,
                            relation=edge_data.get("relation", "related_to"),
                            properties=edge_data.get("properties", {}),
                            weight=edge_data.get("weight", 1.0),
                            created_date=edge_data.get("created_date", ""),
                        )
                    )
                    if source not in visited_nodes:
                        queue.append((source, depth + 1))

        # 3. 构建结果
        result_nodes: list[GraphNode] = []
        for nid in visited_nodes:
            data = self.graph.nodes[nid]
            result_nodes.append(
                GraphNode(
                    node_id=nid,
                    node_type=data.get("node_type", "entity"),
                    label=data.get("label", ""),
                    properties=data.get("properties", {}),
                    weight=data.get("weight", 1.0),
                    created_date=data.get("created_date", ""),
                    last_accessed=data.get("last_accessed", ""),
                    access_count=data.get("access_count", 0),
                )
            )

        # 4. 生成上下文摘要
        context_parts: list[str] = []
        for node in result_nodes[:10]:
            context_parts.append(f"[{node.node_type}]{node.label}")
        for edge in visited_edges[:15]:
            src_label = self.graph.nodes[edge.source_id].get("label", edge.source_id)
            tgt_label = self.graph.nodes[edge.target_id].get("label", edge.target_id)
            context_parts.append(f"{src_label} --{edge.relation}--> {tgt_label}")

        context_summary = "；".join(context_parts)

        return GraphSearchResult(
            nodes=result_nodes,
            edges=visited_edges,
            context_summary=context_summary,
        )

    def find_path(
        self, entity_a: str, entity_b: str, max_hops: int = 5
    ) -> list[GraphEdge]:
        """查找两个实体之间的最短路径"""
        # 先通过标签找节点ID
        a_id = self._find_node_by_label(entity_a)
        b_id = self._find_node_by_label(entity_b)
        if not a_id or not b_id:
            return []

        try:
            path = nx.shortest_path(self.graph, a_id, b_id)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

        if len(path) > max_hops + 1:
            return []

        edges: list[GraphEdge] = []
        for i in range(len(path) - 1):
            edge_data = self.graph.edges[path[i], path[i + 1]]
            edges.append(
                GraphEdge(
                    source_id=path[i],
                    target_id=path[i + 1],
                    relation=edge_data.get("relation", "related_to"),
                    properties=edge_data.get("properties", {}),
                    weight=edge_data.get("weight", 1.0),
                    created_date=edge_data.get("created_date", ""),
                )
            )
        return edges

    def get_timeline(self, entity_id: str) -> list[dict]:
        """获取实体相关的时间线事件"""
        if entity_id not in self.graph:
            # 尝试按标签查找
            entity_id = self._find_node_by_label(entity_id) or entity_id
            if entity_id not in self.graph:
                return []

        events: list[dict] = []
        # 找所有关联的事件节点
        for _, target, data in self.graph.out_edges(entity_id, data=True):
            if data.get("relation") in ("about", "felt_during", "followed_by"):
                target_data = self.graph.nodes[target]
                if target_data.get("node_type") == "event":
                    events.append(
                        {
                            "event_id": target,
                            "label": target_data.get("label", ""),
                            "timestamp": target_data.get("properties", {}).get(
                                "timestamp", ""
                            ),
                            "relation": data.get("relation", ""),
                        }
                    )

        for source, _, data in self.graph.in_edges(entity_id, data=True):
            if data.get("relation") in ("about", "felt_during", "followed_by"):
                source_data = self.graph.nodes[source]
                if source_data.get("node_type") == "event":
                    events.append(
                        {
                            "event_id": source,
                            "label": source_data.get("label", ""),
                            "timestamp": source_data.get("properties", {}).get(
                                "timestamp", ""
                            ),
                            "relation": data.get("relation", ""),
                        }
                    )

        # 按时间排序
        events.sort(key=lambda x: x.get("timestamp", ""))
        return events

    def get_related(self, entity_id: str, max_depth: int = 2) -> GraphSearchResult:
        """获取实体关联的所有节点"""
        if entity_id not in self.graph:
            return GraphSearchResult(
                nodes=[], edges=[], context_summary="未找到该实体"
            )
        return self.search_graph(
            query=self.graph.nodes[entity_id].get("label", entity_id),
            max_depth=max_depth,
            max_nodes=15,
        )

    def decay_graph_weights(self) -> None:
        """图节点/边权重衰减"""
        import time
        start_time = time.monotonic()

        decay_lambda = self.config.WEIGHT_DECAY_LAMBDA
        now = datetime.now()
        for nid, data in self.graph.nodes(data=True):
            created = data.get("created_date", now.strftime("%Y-%m-%d"))
            try:
                days = (now - datetime.strptime(created, "%Y-%m-%d")).days
            except ValueError:
                days = 0
            access_count = data.get("access_count", 0)
            new_weight = math.sqrt(access_count + 1) * math.exp(-decay_lambda * days)
            data["weight"] = max(new_weight, 0.01)

        for u, v, data in self.graph.edges(data=True):
            old_weight = data.get("weight", 1.0)
            data["weight"] = max(old_weight * 0.95, 0.01)

        elapsed = time.monotonic() - start_time
        logger.info(
            "decay_graph_weights completed in %.2fs, %d nodes, %d edges",
            elapsed, self.graph.number_of_nodes(), self.graph.number_of_edges(),
        )

    def reinforce_path(
        self, path_node_ids: list[str], strength: float = 0.1
    ) -> None:
        """强化路径上所有节点的权重"""
        for nid in path_node_ids:
            if nid in self.graph:
                current = self.graph.nodes[nid].get("weight", 1.0)
                self.graph.nodes[nid]["weight"] = min(current + strength, 2.0)
                self.graph.nodes[nid]["access_count"] = (
                    self.graph.nodes[nid].get("access_count", 0) + 1
                )

    def save_graph(self) -> None:
        """持久化图谱到JSON"""
        os.makedirs(self.config.graphrag_db_dir, exist_ok=True)
        graph_path = os.path.join(
            self.config.graphrag_db_dir, "episodic_graph.json"
        )

        data = nx.node_link_data(self.graph)
        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(
            "Graph saved: %d nodes, %d edges",
            self.graph.number_of_nodes(),
            self.graph.number_of_edges(),
        )

    def load_graph(self) -> nx.DiGraph:
        """从JSON加载图谱"""
        graph_path = os.path.join(
            self.config.graphrag_db_dir, "episodic_graph.json"
        )
        if os.path.exists(graph_path):
            try:
                with open(graph_path, encoding="utf-8") as f:
                    data = json.load(f)
                g = nx.node_link_graph(data, directed=True)
                logger.info(
                    "Graph loaded: %d nodes, %d edges",
                    g.number_of_nodes(),
                    g.number_of_edges(),
                )
                return g
            except Exception as e:
                logger.warning("Failed to load graph, starting fresh: %s", e)
        return nx.DiGraph()

    def get_stats(self) -> dict:
        """获取图谱统计信息"""
        node_types: dict[str, int] = {}
        for _, data in self.graph.nodes(data=True):
            ntype = data.get("node_type", "entity")
            node_types[ntype] = node_types.get(ntype, 0) + 1

        return {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "node_types": node_types,
        }

    def _find_node_by_label(self, label: str) -> str | None:
        """通过标签查找节点ID - 确匹配优先，模糊匹配按相似度排序"""
        label_lower = label.lower()

        # 1. Exact match (highest priority)
        for nid, data in self.graph.nodes(data=True):
            if data.get("label", "").lower() == label_lower:
                return nid

        # 2. Fuzzy match: collect all substring matches, sort by label length diff
        # Shorter difference = closer match (e.g., "猫" prefers "猫" over "小猫咪")
        candidates: list[tuple[int, str]] = []
        for nid, data in self.graph.nodes(data=True):
            node_label = data.get("label", "").lower()
            if label_lower in node_label:
                length_diff = abs(len(node_label) - len(label_lower))
                candidates.append((length_diff, nid))

        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]

        return None
