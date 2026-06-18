import uuid
import numpy as np
from sklearn.cluster import KMeans
from backend.embeddings.hf_client import get_embedding, generate_text
from backend.database.qdrant_db import upsert_chunks

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """Splits a document into overlapping character chunks."""
    if len(text) <= chunk_size:
        return [text]
        
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
        
    return chunks

def summarize_cluster(texts: list[str], startup_name: str) -> str:
    """Uses LLM to summarize a group of related text chunks."""
    combined_text = "\n\n".join([f"- {t}" for t in texts])
    prompt = f"""
    You are an AI market intelligence researcher compiling a summary for {startup_name}.
    Synthesize and summarize the following points into a coherent, informative paragraph.
    Focus on business activities, technologies, products, or events.
    Keep the summary professional and concise.
    
    POINTS:
    {combined_text[:3000]}
    
    SUMMARY:
    """
    messages = [
        {"role": "system", "content": "You are a professional business researcher."},
        {"role": "user", "content": prompt}
    ]
    return generate_text(messages, temperature=0.3)

def build_raptor_tree(startup_name: str, documents: list[str]) -> str:
    """
    Builds a hierarchical RAPTOR tree from raw documents.
    Level 0: Raw chunks.
    Level 1: Summaries of Level 0 clusters.
    Level 2: Summaries of Level 1 clusters (if needed).
    Level 3: Global company summary.
    
    Returns the Level 3 (Global) summary.
    """
    # 1. Generate Level 0 Chunks
    l0_texts = []
    for doc in documents:
        l0_texts.extend(chunk_text(doc))
        
    if not l0_texts:
        return f"No documentation found for {startup_name}."
        
    l0_embeddings = [get_embedding(t) for t in l0_texts]
    
    # Structure points for Qdrant
    qdrant_points = []
    l0_ids = [str(uuid.uuid4()) for _ in l0_texts]
    
    for i, (text, emb, uid) in enumerate(zip(l0_texts, l0_embeddings, l0_ids)):
        qdrant_points.append({
            "id": uid,
            "vector": emb,
            "payload": {
                "startup_name": startup_name,
                "text": text,
                "level": 0,
                "parent_id": None
            }
        })
        
    # 2. Cluster & Summarize Level 0 -> Level 1
    num_l0 = len(l0_texts)
    l1_texts = []
    l1_ids = []
    
    if num_l0 > 1:
        # Determine number of clusters (typically 3-4 chunks per cluster)
        num_clusters = max(1, num_l0 // 3)
        # Handle case where num_clusters >= num_l0
        num_clusters = min(num_clusters, num_l0 - 1)
        if num_clusters == 0:
            num_clusters = 1
            
        embeddings_matrix = np.array(l0_embeddings)
        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init="auto")
        labels = kmeans.fit_predict(embeddings_matrix)
        
        # Group chunks by cluster
        clusters = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)
            
        # Summarize each cluster
        for label, idxs in clusters.items():
            cluster_texts = [l0_texts[idx] for idx in idxs]
            summary = summarize_cluster(cluster_texts, startup_name)
            l1_texts.append(summary)
            
            l1_uid = str(uuid.uuid4())
            l1_ids.append(l1_uid)
            l1_emb = get_embedding(summary)
            
            qdrant_points.append({
                "id": l1_uid,
                "vector": l1_emb,
                "payload": {
                    "startup_name": startup_name,
                    "text": summary,
                    "level": 1,
                    "parent_id": None
                }
            })
            
            # Update children's parent references
            for idx in idxs:
                qdrant_points[idx]["payload"]["parent_id"] = l1_uid
    else:
        # Single chunk, duplicate to Level 1
        summary = summarize_cluster(l0_texts, startup_name)
        l1_texts.append(summary)
        l1_uid = str(uuid.uuid4())
        l1_ids.append(l1_uid)
        l1_emb = get_embedding(summary)
        
        qdrant_points.append({
            "id": l1_uid,
            "vector": l1_emb,
            "payload": {
                "startup_name": startup_name,
                "text": summary,
                "level": 1,
                "parent_id": None
            }
        })
        qdrant_points[0]["payload"]["parent_id"] = l1_uid

    # 3. Create Level 2 (Market/Higher level Summaries) if there are many Level 1 clusters
    l2_texts = []
    l2_ids = []
    if len(l1_texts) > 3:
        num_clusters = max(1, len(l1_texts) // 3)
        num_clusters = min(num_clusters, len(l1_texts) - 1)
        
        l1_embs = [get_embedding(t) for t in l1_texts]
        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init="auto")
        labels = kmeans.fit_predict(np.array(l1_embs))
        
        clusters = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)
            
        for label, idxs in clusters.items():
            cluster_texts = [l1_texts[idx] for idx in idxs]
            summary = summarize_cluster(cluster_texts, startup_name)
            l2_texts.append(summary)
            
            l2_uid = str(uuid.uuid4())
            l2_ids.append(l2_uid)
            l2_emb = get_embedding(summary)
            
            qdrant_points.append({
                "id": l2_uid,
                "vector": l2_emb,
                "payload": {
                    "startup_name": startup_name,
                    "text": summary,
                    "level": 2,
                    "parent_id": None
                }
            })
            
            # Update parent of L1 nodes
            for p in qdrant_points:
                if p["payload"]["level"] == 1 and p["id"] in [l1_ids[idx] for idx in idxs]:
                    p["payload"]["parent_id"] = l2_uid
    else:
        # Just use Level 1 texts directly
        l2_texts = l1_texts
        l2_ids = l1_ids

    # 4. Generate Level 3 (Global Summary)
    global_summary = summarize_cluster(l2_texts, startup_name)
    l3_uid = str(uuid.uuid4())
    l3_emb = get_embedding(global_summary)
    
    qdrant_points.append({
        "id": l3_uid,
        "vector": l3_emb,
        "payload": {
            "startup_name": startup_name,
            "text": global_summary,
            "level": 3,
            "parent_id": None
        }
    })
    
    # Update parent of Level 2/1 nodes
    for p in qdrant_points:
        if p["payload"]["parent_id"] is None and p["id"] != l3_uid:
            p["payload"]["parent_id"] = l3_uid
            
    # Save all RAPTOR tree nodes to Qdrant
    upsert_chunks(qdrant_points)
    
    return global_summary
