from app.database import database
from datetime import datetime
from bson import ObjectId

async def create_textbook_metadata(textbook_data: dict):
    """Save only textbook metadata - no full text"""
    textbook_data["created_at"] = datetime.utcnow()
    # Remove extracted_text if it exists - we don't store it anymore
    textbook_data.pop("extracted_text", None)
    
    result = await database.textbooks.insert_one(textbook_data)
    return str(result.inserted_id)

async def update_textbook_processing_status(textbook_id: str, chunk_count: int, total_words: int):
    """Update textbook with processing results"""
    result = await database.textbooks.update_one(
        {"_id": ObjectId(textbook_id)},
        {
            "$set": {
                "chunk_count": chunk_count,
                "total_words": total_words,
                "processed_at": datetime.utcnow(),
                "processing_status": "completed"
            }
        }
    )
    return result.modified_count > 0

async def get_user_textbooks(user_email: str):
    """Get all textbook metadata for a user"""
    textbooks = []
    async for textbook in database.textbooks.find({"user_email": user_email}):
        textbook["_id"] = str(textbook["_id"])
        textbooks.append(textbook)
    return textbooks
