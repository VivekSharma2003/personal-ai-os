"""
Personal AI OS - Vector Database (FAISS) Management
"""
import os
import numpy as np
from typing import Optional, List, Tuple
import faiss

from app.config import get_settings


settings = get_settings()

# Vector store
vector_index: Optional[faiss.Index] = None
embedding_map: dict = {}  # Maps embedding_id to index position
index_to_id: dict = {}  # Maps index position to embedding_id

DIMENSION = 1536  # OpenAI text-embedding-3-small dimension
INDEX_PATH = os.path.join(settings.vector_db_path, "faiss.index")
MAP_PATH = os.path.join(settings.vector_db_path, "embedding_map.npy")


async def init_vector_db():
    """Initialize or load FAISS index."""
    global vector_index, embedding_map, index_to_id
    
    os.makedirs(settings.vector_db_path, exist_ok=True)
    
    if os.path.exists(INDEX_PATH):
        # Load existing index
        vector_index = faiss.read_index(INDEX_PATH)
        if os.path.exists(MAP_PATH):
            data = np.load(MAP_PATH, allow_pickle=True).item()
            embedding_map = data.get("embedding_map", {})
            index_to_id = data.get("index_to_id", {})
    else:
        # Create new index
        vector_index = faiss.IndexFlatIP(DIMENSION)  # Inner product for cosine sim
    

def save_index():
    """Persist index to disk."""
    if vector_index:
        faiss.write_index(vector_index, INDEX_PATH)
        np.save(MAP_PATH, {
            "embedding_map": embedding_map,
            "index_to_id": index_to_id
        })


async def add_embedding(embedding_id: str, embedding: List[float]) -> int:
    """Add an embedding to the index."""
    global embedding_map, index_to_id
    
    if not vector_index:
        raise RuntimeError("Vector index not initialized")
    
    # Normalize for cosine similarity
    vector = np.array([embedding], dtype=np.float32)
    faiss.normalize_L2(vector)
    
    # Add to index
    idx = vector_index.ntotal
    vector_index.add(vector)
    
    # Update maps
    embedding_map[embedding_id] = idx
    index_to_id[idx] = embedding_id
    
    # Save periodically (in production, do this in background)
    if idx % 100 == 0:
        save_index()
    
    return idx


async def search_similar(
    query_embedding: List[float],
    k: int = 5,
    threshold: float = 0.7
) -> List[Tuple[str, float]]:
    """Search for similar embeddings."""
    if not vector_index or vector_index.ntotal == 0:
        return []
    
    # Normalize query
    query = np.array([query_embedding], dtype=np.float32)
    faiss.normalize_L2(query)
    
    # Search
    k = min(k, vector_index.ntotal)
    scores, indices = vector_index.search(query, k)
    
    # Filter by threshold and map to IDs
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx >= 0 and score >= threshold:
            embedding_id = index_to_id.get(int(idx))
            if embedding_id:
                results.append((embedding_id, float(score)))
    
    return results


async def get_embedding_by_id(embedding_id: str) -> Optional[np.ndarray]:
    """Get an embedding by its ID."""
    if embedding_id not in embedding_map:
        return None
    
    idx = embedding_map[embedding_id]
    if vector_index:
        return vector_index.reconstruct(idx)
    return None


async def remove_embedding(embedding_id: str):
    """
    Remove an embedding from the index.
    Note: FAISS doesn't support deletion well, so we just remove from maps.
    Full cleanup would require periodic index rebuilding.
    """
    global embedding_map, index_to_id
    
    if embedding_id in embedding_map:
        idx = embedding_map[embedding_id]
        del embedding_map[embedding_id]
        if idx in index_to_id:
            del index_to_id[idx]
