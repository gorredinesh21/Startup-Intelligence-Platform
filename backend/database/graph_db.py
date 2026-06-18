import os
import json
import sqlite3
import networkx as nx
from dotenv import load_dotenv

load_dotenv()

LOCAL_FALLBACK = os.getenv("LOCAL_FALLBACK", "true").lower() == "true"
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

class LocalGraphEngine:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "graph_fallback.db")
        self.db_path = os.path.abspath(db_path)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                label TEXT,
                properties TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                source TEXT,
                target TEXT,
                type TEXT,
                properties TEXT,
                PRIMARY KEY (source, target, type)
            )
        """)
        conn.commit()
        conn.close()

    def add_node(self, node_id, label, properties=None):
        properties = properties or {}
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO nodes (id, label, properties) VALUES (?, ?, ?)",
            (node_id, label, json.dumps(properties))
        )
        conn.commit()
        conn.close()

    def add_relationship(self, source, target, rel_type, properties=None):
        properties = properties or {}
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Ensure nodes exist
        cursor.execute("SELECT id FROM nodes WHERE id = ?", (source,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO nodes (id, label, properties) VALUES (?, ?, ?)", (source, "Company", "{}"))
        cursor.execute("SELECT id FROM nodes WHERE id = ?", (target,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO nodes (id, label, properties) VALUES (?, ?, ?)", (target, "Company", "{}"))
            
        cursor.execute(
            "INSERT OR REPLACE INTO edges (source, target, type, properties) VALUES (?, ?, ?, ?)",
            (source, target, rel_type, json.dumps(properties))
        )
        conn.commit()
        conn.close()

    def load_networkx(self) -> nx.MultiDiGraph:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        G = nx.MultiDiGraph()
        
        cursor.execute("SELECT id, label, properties FROM nodes")
        for node_id, label, props_json in cursor.fetchall():
            props = json.loads(props_json)
            props["label"] = label
            G.add_node(node_id, **props)
            
        cursor.execute("SELECT source, target, type, properties FROM edges")
        for source, target, rel_type, props_json in cursor.fetchall():
            props = json.loads(props_json)
            props["type"] = rel_type
            G.add_edge(source, target, key=rel_type, **props)
            
        conn.close()
        return G

    def get_neighborhood(self, start_node, depth=2):
        G = self.load_networkx()
        if start_node not in G:
            return {"nodes": [], "edges": []}
            
        # Find nodes within depth hops
        nodes_set = {start_node}
        current_layer = {start_node}
        for _ in range(depth):
            next_layer = set()
            for node in current_layer:
                # Add successors and predecessors for undirected neighborhood traversal
                for neighbor in list(G.successors(node)) + list(G.predecessors(node)):
                    if neighbor not in nodes_set:
                        nodes_set.add(neighbor)
                        next_layer.add(neighbor)
            current_layer = next_layer
            
        subG = G.subgraph(nodes_set)
        
        nodes_list = []
        for n, data in subG.nodes(data=True):
            node_data = dict(data)
            node_data["id"] = n
            nodes_list.append(node_data)
            
        edges_list = []
        for u, v, key, data in subG.edges(keys=True, data=True):
            edge_data = dict(data)
            edge_data["source"] = u
            edge_data["target"] = v
            edge_data["type"] = key
            edges_list.append(edge_data)
            
        return {"nodes": nodes_list, "edges": edges_list}

    def get_all_graph(self):
        G = self.load_networkx()
        nodes_list = [{"id": n, **dict(data)} for n, data in G.nodes(data=True)]
        edges_list = [{"source": u, "target": v, "type": key, **dict(data)} for u, v, key, data in G.edges(keys=True, data=True)]
        return {"nodes": nodes_list, "edges": edges_list}

    def clear_all(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM nodes")
        cursor.execute("DELETE FROM edges")
        conn.commit()
        conn.close()

class Neo4jGraphEngine:
    def __init__(self):
        from neo4j import GraphDatabase
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self.driver.close()

    def add_node(self, node_id, label, properties=None):
        properties = properties or {}
        properties["name"] = node_id  # Align with node_id
        
        # dynamic query based on label
        query = f"MERGE (n:{label} {{name: $name}}) SET n += $props"
        with self.driver.session() as session:
            session.run(query, name=node_id, props=properties)

    def add_relationship(self, source, target, rel_type, properties=None):
        properties = properties or {}
        # Assume source and target are Companies by default if not set, or merge generically
        # To merge dynamically, we first locate source/target or create them
        query = (
            f"MERGE (a:Company {{name: $source}}) "
            f"MERGE (b:Company {{name: $target}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            f"SET r += $props"
        )
        with self.driver.session() as session:
            session.run(query, source=source, target=target, props=properties)

    def get_neighborhood(self, start_node, depth=2):
        # Neo4j query for neighborhood
        query = (
            "MATCH (n {name: $start_node}) "
            f"MATCH path = (n)-[*1..{depth}]-(m) "
            "UNWIND nodes(path) as node "
            "UNWIND relationships(path) as rel "
            "RETURN collect(distinct node) as nodes, collect(distinct rel) as rels"
        )
        with self.driver.session() as session:
            result = session.run(query, start_node=start_node)
            record = result.single()
            if not record:
                return {"nodes": [], "edges": []}
                
            nodes = []
            for n in record["nodes"]:
                node_data = dict(n)
                node_data["id"] = n.get("name") or n.element_id
                node_data["label"] = list(n.labels)[0] if n.labels else "Company"
                nodes.append(node_data)
                
            edges = []
            for r in record["rels"]:
                edge_data = dict(r)
                edge_data["source"] = r.nodes[0].get("name")
                edge_data["target"] = r.nodes[1].get("name")
                edge_data["type"] = r.type
                edges.append(edge_data)
                
            return {"nodes": nodes, "edges": edges}

    def get_all_graph(self):
        query = "MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN n, r, m"
        with self.driver.session() as session:
            result = session.run(query)
            nodes_map = {}
            edges = []
            for record in result:
                n = record["n"]
                if n:
                    nid = n.get("name") or n.element_id
                    nodes_map[nid] = {
                        "id": nid,
                        "label": list(n.labels)[0] if n.labels else "Company",
                        **dict(n)
                    }
                r = record["r"]
                m = record["m"]
                if r and m:
                    edges.append({
                        "source": r.nodes[0].get("name"),
                        "target": r.nodes[1].get("name"),
                        "type": r.type,
                        **dict(r)
                    })
            return {"nodes": list(nodes_map.values()), "edges": edges}

    def clear_all(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

# Factory function
def get_graph_engine():
    if LOCAL_FALLBACK:
        return LocalGraphEngine()
    else:
        return Neo4jGraphEngine()
