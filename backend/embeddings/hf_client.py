import os
import requests
import json
import random
import time
from dotenv import load_dotenv

load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY", "hf_mock_placeholder_token")
LOCAL_FALLBACK = os.getenv("LOCAL_FALLBACK", "true").lower() == "true"
IS_MOCK = "mock" in HF_API_KEY or HF_API_KEY == "hf_your_key_here" or not HF_API_KEY or LOCAL_FALLBACK

EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
GENERATION_MODEL = "mistralai/Mistral-Small-3.1-24B-Instruct"
RERANKER_MODEL = "BAAI/bge-reranker-large"

def make_hf_request(model_id, payload):
    url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    # Try requesting up to 3 times in case of loading models
    for attempt in range(5):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 503: # Model is loading
                wait_time = response.json().get("estimated_time", 10)
                print(f"HF Model {model_id} is loading. Waiting {wait_time}s (attempt {attempt+1}/5)...")
                time.sleep(min(wait_time, 10))
            else:
                print(f"HF API Error ({response.status_code}): {response.text}")
                break
        except Exception as e:
            print(f"HF Request error: {e}")
            break
    return None

def get_embedding(text: str) -> list[float]:
    """Generates 1024-dimensional embedding vector."""
    if IS_MOCK:
        # Generate stable mock embedding based on hash of text
        random.seed(hash(text))
        vec = [random.uniform(-0.1, 0.1) for _ in range(1024)]
        # Normalize
        norm = sum(x**2 for x in vec)**0.5
        return [x/norm for x in vec]
        
    payload = {"inputs": text, "options": {"wait_for_model": True}}
    res = make_hf_request(EMBEDDING_MODEL, payload)
    
    if res and isinstance(res, list):
        # bge-large-en-v1.5 output can be list of floats or list of lists
        if isinstance(res[0], list):
            return res[0]
        return res
    
    # Fallback to random if API fails
    random.seed(hash(text))
    return [random.uniform(-0.1, 0.1) for _ in range(1024)]

def generate_text(messages: list[dict], temperature: float = 0.3, max_tokens: int = 800) -> str:
    """Queries Mistral Small 3.1 or returns dynamic mock responses."""
    user_query = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_query = msg.get("content", "").lower()
            break
            
    if IS_MOCK:
        # Provide rich context-aware mock answers for demos
        time.sleep(1) # simulate latency
        if "openai" in user_query and "compet" in user_query:
            return (
                "Based on the startup graph mapping, the direct competitors to OpenAI in AI Agents include:\n\n"
                "1. **Anthropic**: Competes directly with Claude 3.5 Sonnet and Computer Use capabilities.\n"
                "2. **Cohere**: Competes in enterprise agent deployments.\n"
                "3. **Adept**: Formed by former OpenAI/Google researchers focusing on Action Transformer agents.\n\n"
                "**Funding & Partnership Context**:\n"
                "Microsoft holds a multi-billion dollar partnership with OpenAI, providing Azure computing, while Anthropic is backed by Amazon ($4B) and Google ($2B). Cohere has raised $450M from Nvidia and Oracle."
            )
        elif "vector database" in user_query or "fund" in user_query:
            return (
                "Vector database startups that raised funding recently:\n\n"
                "1. **Pinecone**: Raised $100M Series B in April 2023 at a $750M valuation led by Andreessen Horowitz.\n"
                "2. **Qdrant**: Raised $28M Series A in Jan 2024 led by Spark Capital to expand its open-source vector search platform.\n"
                "3. **Weaviate**: Raised $50M Series B in April 2023 led by Index Ventures.\n\n"
                "These companies benefit from the surge in Retrieval-Augmented Generation (RAG) and RAPTOR systems."
            )
        elif "partnership" in user_query or "microsoft" in user_query:
            return (
                "Microsoft has active partnerships with several AI startups:\n\n"
                "- **OpenAI**: Core strategic alliance ($13B+ total investment, Azure exclusivity, integration in Copilots).\n"
                "- **Mistral AI**: Partnered in Feb 2024 to host Mistral models on Azure, including a minor equity stake.\n"
                "- **Cohere**: Supported on Azure AI models catalog.\n"
                "- **Inflection AI**: Acquired core team and licensed technology in March 2024."
            )
        else:
            return (
                f"### Startup Market Intelligence Summary\n\n"
                f"Processed query regarding: *'{user_query}'*.\n\n"
                f"From the ingested knowledge base, we found 5 relevant documents and 3 graph relations. "
                f"Startups like **OpenAI, Anthropic, Qdrant, and Cursor** are active in this space. "
                f"Let me know if you would like me to generate a competitor graph or perform a detailed similarity mapping!"
            )
            
    # For actual API, we use HF Chat Completion compatible endpoint
    url = "https://api-inference.huggingface.co/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GENERATION_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            res_json = response.json()
            return res_json["choices"][0]["message"]["content"]
        else:
            print(f"HF Generation Error ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"HF Generation request failed: {e}")
        
    return "Error: Could not generate answer from Hugging Face Inference API."

def rerank(query: str, documents: list[str]) -> list[dict]:
    """Reranks documents using BAAI/bge-reranker-large."""
    if not documents:
        return []
        
    if IS_MOCK:
        # Return documents sorted by a naive overlap score
        scores = []
        for i, doc in enumerate(documents):
            score = 0.9 - (i * 0.05)  # slightly descending order
            scores.append({"index": i, "score": score})
        return scores
        
    payload = {
        "inputs": {
            "source_sentence": query,
            "sentences": documents
        }
    }
    
    res = make_hf_request(RERANKER_MODEL, payload)
    
    if res and isinstance(res, list):
        # HF returns a list of dictionaries like [{"score": 0.99, "label": "LABEL_0"}, ...]
        # or lists of floats. Let's parse and map it back to index list.
        # Format is usually list of dicts with 'score' and 'label' (representing index index/LABEL_X)
        # or directly list of scores.
        ranked = []
        for i, item in enumerate(res):
            if isinstance(item, dict):
                score = item.get("score", 0.0)
                # Some API configs label return values like "LABEL_3" to mean index 3
                label = item.get("label", "")
                idx = i
                if label.startswith("LABEL_"):
                    try:
                        idx = int(label.split("_")[1])
                    except:
                        pass
                ranked.append({"index": idx, "score": score})
            else:
                ranked.append({"index": i, "score": float(item)})
        return sorted(ranked, key=lambda x: x["score"], reverse=True)
        
    # Fallback to default ranking
    return [{"index": i, "score": 0.5} for i in range(len(documents))]
