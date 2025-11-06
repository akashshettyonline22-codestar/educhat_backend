from app.database import database
from datetime import datetime
from bson import ObjectId
from typing import List, Dict
import uuid

async def create_textbook_chunks(textbook_id: str, user_email: str, chunks: List[dict], textbook_metadata: dict) -> List[str]:
    """Save textbook chunks with enhanced metadata"""
    
    chunk_documents = []
    chunk_ids = []
    
    for chunk in chunks:
        chunk_id = str(uuid.uuid4())
        chunk_ids.append(chunk_id)
        
        chunk_doc = {
            "_id": chunk_id,
            "textbook_id": textbook_id,
            "user_email": user_email,
            "chunk_number": chunk.get("chunk_number", 1),
            "content": chunk["content"],
            "word_count": chunk.get("word_count", 0),
            "char_count": chunk.get("char_count", 0),
            "page_number": chunk.get("page_number", 1),  # ADD THIS!
            "content_type": chunk.get("content_type", "regular"),
            "created_at": datetime.utcnow(),
            
            # Textbook metadata
            "textbook_name": textbook_metadata["name"],
            "subject": textbook_metadata["subject"], 
            "grade": textbook_metadata["grade"],
            "description": textbook_metadata.get("description", ""),
            "original_filename": textbook_metadata["original_filename"],
            "file_path": textbook_metadata["file_path"]  # ADD THIS!
        }
        
        chunk_documents.append(chunk_doc)
    
    # Bulk insert
    result = await database.textbook_chunks.insert_many(chunk_documents)
    return chunk_ids

async def get_textbook_chunks(textbook_id: str, user_email: str):
    """Get all chunks for a specific textbook"""
    chunks = []
    async for chunk in database.textbook_chunks.find(
        {"textbook_id": textbook_id, "user_email": user_email}
    ).sort("chunk_number", 1):
        chunk["_id"] = str(chunk["_id"])
        chunks.append(chunk)
    return chunks

async def get_user_chunks_by_subject(user_email: str, subject: str = None):
    """Get chunks filtered by subject (for search)"""
    filter_query = {"user_email": user_email}
    if subject:
        filter_query["subject"] = subject
        
    chunks = []
    async for chunk in database.textbook_chunks.find(filter_query):
        chunk["_id"] = str(chunk["_id"])
        chunks.append(chunk)
    return chunks
