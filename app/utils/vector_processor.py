import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Tuple
import os
import pickle
import uuid

# Load sentence transformer model (cached after first use)
model = None

def get_embedding_model():
    """Get or initialize the embedding model"""
    global model
    if model is None:
        print("Loading sentence transformer model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')  # Fast and good quality
        print("Model loaded successfully!")
    return model

def create_embeddings(chunks: List[str]) -> np.ndarray:
    """Convert text chunks to vector embeddings"""
    model = get_embedding_model()
    
    print(f"Creating embeddings for {len(chunks)} chunks...")
    embeddings = model.encode(chunks, show_progress_bar=True)
    
    return embeddings.astype('float32')

def create_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    """Create FAISS index from embeddings"""
    print(f"Creating FAISS index with {embeddings.shape[0]} vectors...")
    
    dimension = embeddings.shape[1]  # Usually 384 for all-MiniLM-L6-v2
    
    # Use IndexFlatIP for cosine similarity (Inner Product after normalization)
    index = faiss.IndexFlatIP(dimension)
    
    # Normalize embeddings for cosine similarity
    faiss.normalize_L2(embeddings)
    
    # Add vectors to index
    index.add(embeddings)
    
    print(f"FAISS index created with dimension {dimension}")
    return index

def save_textbook_vectors(user_email: str, textbook_id: str, index: faiss.Index, chunks: List[str]):
    """Save FAISS index and chunk mapping"""
    
    # Create directories
    os.makedirs("data/indexes", exist_ok=True)
    os.makedirs("data/chunks", exist_ok=True)
    
    # Create safe filename for this textbook
    safe_email = user_email.replace("@", "_").replace(".", "_")
    safe_filename = f"{safe_email}_{textbook_id}"
    
    # Save FAISS index
    index_path = f"data/indexes/{safe_filename}.index"
    faiss.write_index(index, index_path)
    
    # Save chunk text mapping
    chunks_path = f"data/chunks/{safe_filename}.pkl"
    with open(chunks_path, 'wb') as f:
        pickle.dump(chunks, f)
    
    print(f"Vectors saved: {index_path}")
    print(f"Chunks saved: {chunks_path}")
    
    return index_path, chunks_path

def process_chunks_to_vectors(user_email: str, textbook_id: str, chunks: List[dict]) -> Tuple[str, str]:
    """Complete pipeline: chunks -> embeddings -> FAISS index -> save"""
    
    # Extract just the text content from chunks
    chunk_texts = [chunk["content"] for chunk in chunks]
    
    print(f"Processing {len(chunk_texts)} chunks to vectors...")
    
    # Create embeddings
    embeddings = create_embeddings(chunk_texts)
    
    # Create FAISS index
    index = create_faiss_index(embeddings)
    
    # Save everything
    index_path, chunks_path = save_textbook_vectors(user_email, textbook_id, index, chunk_texts)
    
    return index_path, chunks_path

def search_similar_chunks(user_email: str, textbook_id: str, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
    """Search for similar chunks in student's textbook"""
    try:
        print("helloo")
        # Create safe filename
        safe_email = user_email.replace("@", "_").replace(".", "_")
        safe_filename = f"{safe_email}_{textbook_id}"
        
        # Load index and chunks
        index_path = f"data/indexes/{safe_filename}.index"
        chunks_path = f"data/chunks/{safe_filename}.pkl"
        
        if not os.path.exists(index_path) or not os.path.exists(chunks_path):
            print(f"Vector files not found for {safe_filename}")
            return []
        
        # Load FAISS index
        index = faiss.read_index(index_path)
        
        # Load chunks
        with open(chunks_path, 'rb') as f:
            chunks = pickle.load(f)
        
        # Create query embedding
        model = get_embedding_model()
        query_embedding = model.encode([query]).astype('float32')
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = index.search(query_embedding, top_k)
        
        # Return results
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(chunks) and score > 0.3:  # Minimum similarity threshold
                results.append((chunks[idx], float(score)))
        
        return results
        
    except Exception as e:
        print(f"Search error: {e}")
        return []

def get_textbook_vector_info(user_email: str, textbook_id: str) -> dict:
    """Get info about stored vectors for a textbook"""
    safe_email = user_email.replace("@", "_").replace(".", "_")
    safe_filename = f"{safe_email}_{textbook_id}"
    
    index_path = f"data/indexes/{safe_filename}.index"
    chunks_path = f"data/chunks/{safe_filename}.pkl"
    
    info = {
        "has_vectors": False,
        "vector_count": 0,
        "dimension": 0,
        "index_file_exists": os.path.exists(index_path),
        "chunks_file_exists": os.path.exists(chunks_path)
    }
    
    try:
        if os.path.exists(index_path):
            index = faiss.read_index(index_path)
            info["has_vectors"] = True
            info["vector_count"] = index.ntotal
            info["dimension"] = index.d
    except Exception as e:
        print(f"Error reading vector info: {e}")
    
    return info
