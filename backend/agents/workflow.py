import json
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from backend.embeddings.hf_client import get_embedding, generate_text, rerank
from backend.database.graph_db import get_graph_engine
from backend.database.qdrant_db import search_chunks
from backend.database.sql_db import SessionLocal, Startup

# State Definition
class AgentState(TypedDict):
    query: str
    intent: str
    subqueries: List[str]
    entities: List[str]
    graph_data: Dict[str, Any]      # Nodes and edges for UI visualization
    retrieved_texts: List[str]      # Texts gathered from Qdrant/RAPTOR
    reranked_texts: List[str]       # Top texts after reranking
    answer: str
    sources: List[str]

# Node 1: Intent Detection
def detect_intent(state: AgentState) -> Dict[str, Any]:
    query = state["query"]
    prompt = f"""
    Analyze the user search query: "{query}"
    Classify the query into one of these intents:
    1. competitor_search (queries asking about competitors, rivals)
    2. funding_analysis (queries asking about raising capital, funding rounds, valuations)
    3. market_mapping (queries asking about a market landscape, e.g. "AI coding assistants", "vector databases")
    4. company_research (queries asking for detailed profiles or comparisons of specific companies)
    5. trend_discovery (queries looking for emerging startups or general sector trends)
    
    Also, extract any primary company/startup names mentioned in the query.
    
    Return ONLY a JSON object:
    {{
      "intent": "competitor_search|funding_analysis|market_mapping|company_research|trend_discovery",
      "entities": ["CompanyA", "CompanyB"]
    }}
    """
    messages = [
        {"role": "system", "content": "You are a query classification system. Answer in strict JSON."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        res = generate_text(messages, temperature=0.1)
        # clean wrappers
        if "```json" in res:
            res = res.split("```json")[1].split("```")[0].strip()
        elif "```" in res:
            res = res.split("```")[1].split("```")[0].strip()
        data = json.loads(res)
        return {
            "intent": data.get("intent", "company_research"),
            "entities": data.get("entities", [])
        }
    except Exception as e:
        print(f"Intent detection error: {e}")
        # Default fallback
        detected_entities = []
        q_lower = query.lower()
        for c in ["openai", "anthropic", "cohere", "qdrant", "pinecone", "weaviate", "cursor", "windsurf", "microsoft"]:
            if c in q_lower:
                detected_entities.append(c.capitalize())
        return {
            "intent": "company_research",
            "entities": detected_entities
        }

# Node 2: Planner
def plan_subqueries(state: AgentState) -> Dict[str, Any]:
    query = state["query"]
    intent = state["intent"]
    entities = state["entities"]
    
    prompt = f"""
    You are a research planner. Break down this main search query: "{query}" with intent: {intent}.
    Generate exactly 2 to 3 simpler, targeted subqueries to gather comprehensive background.
    
    Example: "Who competes with OpenAI in AI agents?"
    Subqueries:
    1. "OpenAI competitors in AI agents"
    2. "List of startups building AI agents"
    3. "OpenAI products and technology stack"
    
    Return ONLY a JSON array of strings, e.g., ["subquery1", "subquery2"].
    """
    messages = [
        {"role": "system", "content": "You are a planner. Return ONLY a JSON list of strings."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        res = generate_text(messages, temperature=0.2)
        if "```json" in res:
            res = res.split("```json")[1].split("```")[0].strip()
        elif "```" in res:
            res = res.split("```")[1].split("```")[0].strip()
        subqueries = json.loads(res)
        if isinstance(subqueries, list):
            return {"subqueries": subqueries}
    except Exception as e:
        print(f"Planner error: {e}")
        
    # Default subqueries fallback
    if entities:
        return {"subqueries": [f"{entities[0]} profile", f"{entities[0]} competitors", f"{entities[0]} funding"]}
    return {"subqueries": [query]}

# Node 3: Graph Retrieval
def retrieve_graph(state: AgentState) -> Dict[str, Any]:
    entities = state["entities"]
    intent = state["intent"]
    graph_engine = get_graph_engine()
    
    combined_graph = {"nodes": [], "edges": []}
    seen_nodes = set()
    seen_edges = set()
    
    # If no entities extracted, pull the whole small graph for context
    if not entities:
        all_graph = graph_engine.get_all_graph()
        return {"graph_data": all_graph}
        
    for entity in entities:
        # Fetch neighborhood up to 2 hops
        neighborhood = graph_engine.get_neighborhood(entity, depth=2)
        for node in neighborhood["nodes"]:
            nid = node["id"]
            if nid not in seen_nodes:
                seen_nodes.add(nid)
                combined_graph["nodes"].append(node)
                
        for edge in neighborhood["edges"]:
            edge_key = (edge["source"], edge["target"], edge["type"])
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                combined_graph["edges"].append(edge)
                
    return {"graph_data": combined_graph}

# Node 4: RAPTOR Retrieval
def retrieve_raptor(state: AgentState) -> Dict[str, Any]:
    query = state["query"]
    subqueries = state.get("subqueries", [query])
    entities = state["entities"]
    
    all_chunks = []
    seen_chunk_texts = set()
    
    # We query for both the main query and each subquery
    search_queries = [query] + subqueries
    for q in list(set(search_queries)):
        q_emb = get_embedding(q)
        
        # Pull from multiple levels (RAPTOR Tree search)
        # Search Level 1-2 (summaries) first for high-level concepts
        summary_results = search_chunks(q_emb, limit=4, level_filter=1) + search_chunks(q_emb, limit=2, level_filter=2)
        
        # Search Level 0 (raw details)
        raw_results = search_chunks(q_emb, limit=4, level_filter=0)
        
        # Collect them
        for r in summary_results + raw_results:
            text = r["payload"].get("text", "")
            startup = r["payload"].get("startup_name", "")
            level = r["payload"].get("level", 0)
            
            if text and text not in seen_chunk_texts:
                seen_chunk_texts.add(text)
                all_chunks.append({
                    "text": text,
                    "startup": startup,
                    "level": level,
                    "score": r["score"]
                })
                
    # Sort by vector search score
    all_chunks = sorted(all_chunks, key=lambda x: x["score"], reverse=True)
    return {"retrieved_texts": [f"[{c['startup']} (L{c['level']})]: {c['text']}" for c in all_chunks[:12]]}

# Node 5: Reranker
def rerank_nodes(state: AgentState) -> Dict[str, Any]:
    query = state["query"]
    retrieved_texts = state["retrieved_texts"]
    
    if not retrieved_texts:
        return {"reranked_texts": []}
        
    # Format texts for reranker (strip source prefix if reranking just text)
    rerank_results = rerank(query, retrieved_texts)
    
    reranked = []
    # Take top 5 chunks
    for res in rerank_results[:6]:
        idx = res["index"]
        reranked.append(retrieved_texts[idx])
        
    return {"reranked_texts": reranked}

# Node 6: Answer Generation
def generate_answer(state: AgentState) -> Dict[str, Any]:
    query = state["query"]
    intent = state["intent"]
    reranked_texts = state["reranked_texts"]
    graph_data = state["graph_data"]
    
    # Compile graph relationships context
    graph_relationships = []
    for edge in graph_data.get("edges", []):
        graph_relationships.append(f"- {edge['source']} {edge['type']} {edge['target']}")
    relations_context = "\n".join(graph_relationships)
    
    documents_context = "\n\n".join(reranked_texts)
    
    prompt = f"""
    You are a premium AI market intelligence analyst for the "Startup Intelligence Platform".
    Answer this query: "{query}"
    
    Use the following extracted database relationships and document contexts to support your answer. 
    Make your output comprehensive, citing sources (e.g., [StartupName (L0)], [StartupName (L1)]) where appropriate.
    If the query asks for a comparison, structure it as a clean markdown table.
    
    DATABASE GRAPH RELATIONSHIPS (NEO4J):
    {relations_context if relations_context else "No graph relations available."}
    
    DOCUMENT HIERARCHY CONTEXT (RAPTOR):
    {documents_context if documents_context else "No RAPTOR document chunks available."}
    
    Be objective, precise, and state clear insights. Make the formatting elegant and executive-level.
    """
    
    messages = [
        {"role": "system", "content": "You are a professional Startup Intelligence Platform analyst."},
        {"role": "user", "content": prompt}
    ]
    
    answer = generate_text(messages, temperature=0.3, max_tokens=1200)
    
    # Extract sources from the reranked texts
    sources = []
    for text in reranked_texts:
        # e.g., "[OpenAI (L1)]: some text" -> source is "OpenAI"
        if text.startswith("["):
            parts = text.split("]:")
            source_info = parts[0][1:]
            if source_info not in sources:
                sources.append(source_info)
                
    return {
        "answer": answer,
        "sources": sources
    }

# Build LangGraph workflow
def build_agent_graph():
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("intent_detection", detect_intent)
    workflow.add_node("planner", plan_subqueries)
    workflow.add_node("graph_retrieval", retrieve_graph)
    workflow.add_node("raptor_retrieval", retrieve_raptor)
    workflow.add_node("reranker", rerank_nodes)
    workflow.add_node("generator", generate_answer)
    
    # Set entry point
    workflow.set_entry_point("intent_detection")
    
    # Add transitions
    workflow.add_edge("intent_detection", "planner")
    workflow.add_edge("planner", "graph_retrieval")
    workflow.add_edge("graph_retrieval", "raptor_retrieval")
    workflow.add_edge("raptor_retrieval", "reranker")
    workflow.add_edge("reranker", "generator")
    workflow.add_edge("generator", END)
    
    return workflow.compile()

agent_app = build_agent_graph()

def run_agent(query: str) -> Dict[str, Any]:
    initial_state = {
        "query": query,
        "intent": "",
        "subqueries": [],
        "entities": [],
        "graph_data": {"nodes": [], "edges": []},
        "retrieved_texts": [],
        "reranked_texts": [],
        "answer": "",
        "sources": []
    }
    return agent_app.invoke(initial_state)
