"""知识图谱数据库客户端（Neo4j + Mock 降级）。

生产环境：连接 Neo4j，使用 Cypher 查询。
Mock 模式：内存邻接表图，实现相同查询接口。
"""
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logger import logger


class InMemoryGraph:
    """内存图（Mock），支持节点/关系与简单 Cypher 语义。"""

    def __init__(self):
        self._nodes: Dict[str, Dict[str, Any]] = {}      # node_id -> props
        self._edges: List[Tuple[str, str, str]] = []     # (from_id, rel, to_id)

    def upsert_node(self, label: str, name: str, props: Optional[dict] = None) -> str:
        node_id = f"{label}:{name}"
        node_props = {"label": label, "name": name, **(props or {})}
        if node_id not in self._nodes:
            self._nodes[node_id] = node_props
        else:
            self._nodes[node_id].update(props or {})
        return node_id

    def add_relation(self, from_label: str, from_name: str,
                     rel: str, to_label: str, to_name: str) -> None:
        f = self.upsert_node(from_label, from_name)
        t = self.upsert_node(to_label, to_name)
        edge = (f, rel, t)
        if edge not in self._edges:
            self._edges.append(edge)

    def query_nodes_by_relation(self, from_label: str, rel: str,
                                to_label: str, to_name: str) -> List[Dict[str, Any]]:
        """查询：X -[:rel]-> (to_label{name:to_name})，返回 X。"""
        results = []
        for f, r, t in self._edges:
            if r == rel and t == f"{to_label}:{to_name}":
                if from_label in ("*",) or self._nodes[f]["label"] == from_label:
                    results.append(self._nodes[f])
        return results

    def traverse_path(self, start_label: str, start_name: str,
                      max_depth: int = 4) -> List[Dict[str, Any]]:
        """从起点做 BFS，返回可达的路径节点序列。"""
        start_id = f"{start_label}:{start_name}"
        if start_id not in self._nodes:
            return []
        # BFS
        from collections import deque

        visited = {start_id}
        paths: List[Dict[str, Any]] = [self._nodes[start_id]]
        queue = deque([start_id])
        depth = 0
        while queue and depth < max_depth:
            size = len(queue)
            for _ in range(size):
                cur = queue.popleft()
                for f, rel, t in self._edges:
                    if f == cur and t not in visited:
                        visited.add(t)
                        paths.append({"node": self._nodes[t], "rel": rel})
                        queue.append(t)
            depth += 1
        return paths

    def find_related(self, name: str) -> List[Dict[str, Any]]:
        """查找与 name 直接相连的实体与关系。"""
        results = []
        for f, rel, t in self._edges:
            if name in f or name in t:
                results.append({
                    "from": self._nodes.get(f, {}).get("name", f),
                    "relation": rel,
                    "to": self._nodes.get(t, {}).get("name", t),
                })
        return results


class Neo4jGraph:
    """Neo4j 图数据库。"""

    def __init__(self):
        self._driver = None

    def connect(self):
        try:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
            self._driver.verify_connectivity()
            logger.info("neo4j connected: %s", settings.NEO4J_URI)
        except Exception as e:
            logger.warning("neo4j connect failed: %s", e)
        return self

    def _run(self, cypher: str, **params):
        if self._driver is None:
            return []
        with self._driver.session() as session:
            result = session.run(cypher, **params)
            return [dict(r) for r in result]

    def upsert_node(self, label: str, name: str, props: Optional[dict] = None) -> str:
        self._run(
            f"MERGE (n:{label} {{name: $name}}) SET n += $props RETURN n.name",
            name=name, props=props or {},
        )
        return f"{label}:{name}"

    def add_relation(self, from_label: str, from_name: str,
                     rel: str, to_label: str, to_name: str) -> None:
        rel_upper = rel.upper().replace(" ", "_")
        self._run(
            f"""
            MERGE (a:{from_label} {{name: $from_name}})
            MERGE (b:{to_label} {{name: $to_name}})
            MERGE (a)-[:{rel_upper}]->(b)
            """,
            from_name=from_name, to_name=to_name,
        )

    def query_nodes_by_relation(self, from_label: str, rel: str,
                                to_label: str, to_name: str) -> List[Dict[str, Any]]:
        rel_upper = rel.upper().replace(" ", "_")
        rows = self._run(
            f"""
            MATCH (a:{from_label})-[r:{rel_upper}]->(b:{to_label} {{name: $to_name}})
            RETURN a.name AS name, labels(a) AS labels, properties(a) AS props
            """,
            to_name=to_name,
        )
        return [{"name": r["name"], "label": r["labels"][0], **r["props"]} for r in rows]

    def traverse_path(self, start_label: str, start_name: str,
                      max_depth: int = 4) -> List[Dict[str, Any]]:
        rows = self._run(
            f"""
            MATCH p=(a:{start_label} {{name: $name}})-[*1..{max_depth}]->(b)
            RETURN b.name AS name, labels(b) AS labels, properties(b) AS props
            LIMIT 50
            """,
            name=start_name,
        )
        return [{"name": r["name"], "label": r["labels"][0], **r["props"]} for r in rows]

    def find_related(self, name: str) -> List[Dict[str, Any]]:
        rows = self._run(
            """
            MATCH (a)-[r]->(b)
            WHERE a.name = $name OR b.name = $name
            RETURN a.name AS from, type(r) AS relation, b.name AS to
            LIMIT 50
            """,
            name=name,
        )
        return rows


class GraphStore:
    """统一入口。"""

    def __init__(self):
        if settings.USE_MOCK:
            self._backend = InMemoryGraph()
        else:
            self._backend = Neo4jGraph()
            self._backend.connect()

    @property
    def backend(self):
        return self._backend

    def upsert_node(self, label: str, name: str, props: Optional[dict] = None) -> str:
        return self._backend.upsert_node(label, name, props)

    def add_relation(self, from_label: str, from_name: str,
                     rel: str, to_label: str, to_name: str) -> None:
        self._backend.add_relation(from_label, from_name, rel, to_label, to_name)

    def query_nodes_by_relation(self, from_label: str, rel: str,
                                to_label: str, to_name: str) -> List[Dict[str, Any]]:
        return self._backend.query_nodes_by_relation(from_label, rel, to_label, to_name)

    def traverse_path(self, start_label: str, start_name: str,
                      max_depth: int = 4) -> List[Dict[str, Any]]:
        return self._backend.traverse_path(start_label, start_name, max_depth)

    def find_related(self, name: str) -> List[Dict[str, Any]]:
        return self._backend.find_related(name)


_graph_store: Optional[GraphStore] = None


def get_graph_store() -> GraphStore:
    global _graph_store
    if _graph_store is None:
        _graph_store = GraphStore()
    return _graph_store
