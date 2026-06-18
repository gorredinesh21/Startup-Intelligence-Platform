import os
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest_models
from dotenv import load_dotenv

load_dotenv()

LOCAL_FALLBACK = os.getenv("LOCAL_FALLBACK", "true").lower() == "true"
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")

COLLECTION_NAME = "raptor_chunks"
VECTOR_DIMENSION = 1024  # Dimension of BAAI/bge-large-en-v1.5

_client = None

def get_qdrant_client():
    global _client
    if _client is not None:
        return _client
        
    if LOCAL_FALLBACK:
        # File-based local storage client
        db_path = os.path.join(os.path.dirname(__file__), "..", "qdrant_local_db")
        os.makedirs(db_path, exist_ok=True)
        _client = QdrantClient(path=db_path)
    else:
        # Connect to remote or local Qdrant server
        _client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY if QDRANT_API_KEY else None
        )
    return _client


def init_qdrant():
    client = get_qdrant_client()
    # Check if collection exists
    collections = client.get_collections().collections
    exists = any(c.name == COLLECTION_NAME for c in collections)
    
    if not exists:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=rest_models.VectorParams(
                size=VECTOR_DIMENSION,
                distance=rest_models.Distance.COSINE
            )
        )
        print(f"Created collection '{COLLECTION_NAME}' in Qdrant.")

def upsert_chunks(points):
    """
    points is a list of dicts with:
    - id: int or str (UUID)
    - vector: list of floats
    - payload: dict containing chunk data (startup_name, text, level, parent_id, etc.)
    """
    client = get_qdrant_client()
    qdrant_points = [
        rest_models.PointStruct(
            id=p["id"],
            vector=p["vector"],
            payload=p["payload"]
        )
        for p in points
    ]
    client.upsert(
        collection_name=COLLECTION_NAME,
        wait=True,
        points=qdrant_points
    )

def search_chunks(query_vector, limit=5, level_filter=None, startup_filter=None):
    client = get_qdrant_client()
    
    must_conditions = []
    if level_filter is not None:
        must_conditions.append(
            rest_models.FieldCondition(
                key="level",
                match=rest_models.MatchValue(value=level_filter)
            )
        )
    if startup_filter is not None:
        must_conditions.append(
            rest_models.FieldCondition(
                key="startup_name",
                match=rest_models.MatchValue(value=startup_filter)
            )
        )
        
    query_filter = None
    if must_conditions:
        query_filter = rest_models.Filter(must=must_conditions)
        
    res = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit,
        query_filter=query_filter
    )
    
    return [
        {
            "id": r.id,
            "score": r.score,
            "payload": r.payload
        }
        for r in res.points
    ]
