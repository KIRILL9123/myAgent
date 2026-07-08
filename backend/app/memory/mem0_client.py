import os
from mem0 import Memory

QDRANT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "qdrant_db")

# Ensure the directory exists
os.makedirs(QDRANT_PATH, exist_ok=True)

config = {
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "qwen2.5:7b",
            "temperature": 0.1,
            "max_tokens": 1000,
        }
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text"
        }
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "agent_memory",
            "path": QDRANT_PATH,
            "embedding_model_dims": 768
        }
    }
}

# Singleton memory instance
mem0 = Memory.from_config(config)

def add_fact(text: str, user_id: str = "kyrylo"):
    """
    Extracts and saves facts from the given text.
    """
    mem0.add(text, user_id=user_id)

def search_facts(query: str, user_id: str = "kyrylo", limit: int = 5) -> str:
    """
    Searches for relevant facts and returns them as a single string.
    """
    results = mem0.search(query, filters={"user_id": user_id}, limit=limit)
    if not results:
        return ""
        
    # Mem0 search can return a list or a dict containing a 'results' key
    if isinstance(results, dict) and "results" in results:
        results = results["results"]
    elif isinstance(results, dict):
        # In case it returned a single memory dict by accident
        results = [results]
        
    facts = []
    for r in results:
        if isinstance(r, dict):
            fact_text = r.get("memory") or r.get("text") or r.get("fact") or str(r)
        else:
            try:
                # Handle pydantic models or objects
                fact_text = r.memory if hasattr(r, "memory") else str(r)
            except Exception:
                fact_text = str(r)
        facts.append(fact_text)
    
    return "\n".join([f"- {f}" for f in facts])
