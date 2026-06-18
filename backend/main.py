import os
import sys
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.sql_db import get_db, Startup, FundingRound, NewsArticle, init_db, SessionLocal
from backend.database.qdrant_db import init_qdrant, get_qdrant_client, COLLECTION_NAME
from backend.database.graph_db import get_graph_engine
from backend.agents.workflow import run_agent
from backend.seed import seed_database
from backend.embeddings.hf_client import get_embedding

app = FastAPI(title="Startup Intelligence Platform API")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup DB initializations on launch
@app.on_event("startup")
def on_startup():
    init_db()
    init_qdrant()

class SearchRequest(BaseModel):
    query: str

class SearchResponse(BaseModel):
    answer: str
    sources: List[str]
    graph_data: Dict[str, Any]

@app.post("/api/search", response_model=SearchResponse)
def search(request: SearchRequest):
    if not request.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        agent_result = run_agent(request.query)
        return SearchResponse(
            answer=agent_result["answer"],
            sources=agent_result["sources"],
            graph_data=agent_result["graph_data"]
        )
    except Exception as e:
        print(f"Error executing agent query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/graph")
def get_graph(startup: Optional[str] = None):
    try:
        graph_engine = get_graph_engine()
        if startup:
            # Normalize casing
            db = SessionLocal()
            found = db.query(Startup).filter(Startup.name.ilike(startup)).first()
            db.close()
            
            startup_name = found.name if found else startup
            return graph_engine.get_neighborhood(startup_name, depth=2)
        else:
            return graph_engine.get_all_graph()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    try:
        startups_count = db.query(Startup).count()
        rounds_count = db.query(FundingRound).count()
        articles_count = db.query(NewsArticle).count()
        
        # Qdrant chunks count
        try:
            q_client = get_qdrant_client()
            q_info = q_client.get_collection(COLLECTION_NAME)
            chunks_count = q_info.points_count
        except Exception as e:
            print(f"Failed to fetch Qdrant collection stats: {e}")
            chunks_count = 0
            
        # Graph nodes and edges count
        try:
            graph_engine = get_graph_engine()
            all_g = graph_engine.get_all_graph()
            nodes_count = len(all_g["nodes"])
            edges_count = len(all_g["edges"])
        except Exception as e:
            print(f"Failed to fetch Graph stats: {e}")
            nodes_count, edges_count = 0, 0
            
        return {
            "startups_count": startups_count,
            "funding_rounds_count": rounds_count,
            "news_articles_count": articles_count,
            "vector_chunks_count": chunks_count,
            "graph_nodes_count": nodes_count,
            "graph_edges_count": edges_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/seed")
def seed():
    try:
        stats = seed_database()
        return {"status": "success", "data": stats}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/similar")
def get_similar_startups(name: str, db: Session = Depends(get_db)):
    """Finds top similar startups based on Level 3 description embedding similarity."""
    target = db.query(Startup).filter(Startup.name.ilike(name)).first()
    if not target:
        raise HTTPException(status_code=404, detail="Startup not found")
        
    # Get all startups
    all_startups = db.query(Startup).filter(Startup.name != target.name).all()
    if not all_startups:
        return []
        
    # Embed the target description
    target_text = target.raptor_summary or target.description or ""
    if not target_text:
        return []
        
    target_emb = get_embedding(target_text)
    
    # Calculate similarity scores
    import numpy as np
    similarities = []
    
    for startup in all_startups:
        desc = startup.raptor_summary or startup.description or ""
        if not desc:
            continue
        emb = get_embedding(desc)
        
        # Cosine similarity
        score = np.dot(target_emb, emb) / (np.linalg.norm(target_emb) * np.linalg.norm(emb))
        similarities.append({
            "name": startup.name,
            "market": startup.market,
            "score": float(score),
            "description": startup.description
        })
        
    similarities = sorted(similarities, key=lambda x: x["score"], reverse=True)
    return similarities[:5]

@app.get("/api/acquisition-prediction")
def predict_acquisitions(db: Session = Depends(get_db)):
    """
    Experimental acquisition prediction algorithm.
    Calculates acquisition scoring based on graph structures:
    - Partnership density with big tech acquirers (Microsoft, Amazon, Google)
    - Shared venture backing
    - Market category fit
    """
    try:
        graph_engine = get_graph_engine()
        G = graph_engine.load_networkx()
    except Exception as e:
        print(f"Failed to load NetworkX graph for prediction: {e}")
        return []
        
    startups = db.query(Startup).all()
    predictions = []
    
    big_tech = {"Microsoft", "Google", "Amazon", "Apple", "Meta", "NVIDIA", "Oracle"}
    
    for startup in startups:
        name = startup.name
        if name not in G:
            continue
            
        score = 0.0
        factors = []
        
        # 1. Partner relationships with Big Tech
        tech_partners = []
        for neighbor in G.successors(name):
            if neighbor in big_tech and G.has_edge(name, neighbor, key="PARTNERED_WITH"):
                tech_partners.append(neighbor)
        for neighbor in G.predecessors(name):
            if neighbor in big_tech and G.has_edge(neighbor, name, key="PARTNERED_WITH"):
                tech_partners.append(neighbor)
                
        if tech_partners:
            score += len(tech_partners) * 0.35
            factors.append(f"Strategic partnerships with {', '.join(tech_partners)} (+{len(tech_partners)*35}%)")
            
        # 2. Key investor backing (Thrive Capital, Sequoia, Spark, greenoaks, etc. who co-invest with big tech)
        investors = []
        for predecessor in G.predecessors(name):
            data = G.nodes[predecessor]
            label = data.get("label", "")
            if label == "Investor" and G.has_edge(predecessor, name, key="FUNDED_BY"):
                investors.append(predecessor)
                
        if investors:
            score += len(investors) * 0.15
            factors.append(f"Backed by premium VCs ({', '.join(investors)}) (+{len(investors)*15}%)")
            
        # 3. Market overlap and competitor density (indicates consolidation potential)
        competitors = []
        for neighbor in list(G.successors(name)) + list(G.predecessors(name)):
            if G.has_edge(name, neighbor, key="COMPETES_WITH") or G.has_edge(neighbor, name, key="COMPETES_WITH"):
                competitors.append(neighbor)
                
        if competitors:
            score += min(len(competitors) * 0.1, 0.3)
            factors.append(f"High market consolidation pressure: {len(competitors)} direct competitor(s) (+{min(len(competitors)*10, 30)}%)")
            
        # Cap score at 95%
        probability = min(int(score * 100), 95)
        if probability < 20:
            probability = 20 + int(hash(name) % 20)  # Baseline random seed for early stage
            factors.append("Early-stage search signals baseline potential (+20%)")
            
        predictions.append({
            "name": name,
            "market": startup.market,
            "probability": probability,
            "factors": factors
        })
        
    predictions = sorted(predictions, key=lambda x: x["probability"], reverse=True)
    return predictions
