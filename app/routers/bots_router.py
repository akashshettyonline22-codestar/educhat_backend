from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.security import HTTPBearer
from app.database import database
import os

router = APIRouter(prefix="/bots", tags=["Bots"])
security = HTTPBearer()


@router.get("/")
async def get_all_bots(
    request: Request,
    token: str = Depends(security)
):
    """Get all available chatbots for the authenticated user"""
    user_email = request.state.current_user_email
    
    try:
        # Get all textbooks for user (each textbook = one bot)
        bots = await database.textbook_chunks.aggregate([
            {"$match": {"user_email": user_email}},
            {"$group": {
                "_id": "$textbook_id",
                "bot_name": {"$first": "$textbook_name"},
                "subject": {"$first": "$subject"},
                "grade": {"$first": "$grade"},
                "description": {"$first": "$description"},
                "created_at": {"$first": "$created_at"}
            }},
            {"$sort": {"created_at": -1}}
        ]).to_list(length=None)
        
        # Format response
        bots_list = [
            {
                "bot_id": bot["_id"],
                "bot_name": bot["bot_name"],
                "subject": bot["subject"],
                "grade": bot["grade"],
                "description": bot.get("description", "")
            }
            for bot in bots
        ]
        
        return {
            "success": True,
            "total_bots": len(bots_list),
            "bots": bots_list
        }
        
    except Exception as e:
        print(f"Error fetching bots: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{bot_id}")
async def delete_bot(
    bot_id: str,
    request: Request,
    token: str = Depends(security)
):
    """Delete a bot and all its associated data"""
    user_email = request.state.current_user_email
    
    try:
        print(f"🗑️ Deleting bot: {bot_id} for user: {user_email}")
        
        # 1. Check if bot exists
        bot = await database.textbook_chunks.find_one({
            "textbook_id": bot_id,
            "user_email": user_email
        })
        
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        bot_name = bot.get("textbook_name", "Unknown")
        
        # 2. Delete textbook chunks from MongoDB
        chunks_result = await database.textbook_chunks.delete_many({
            "textbook_id": bot_id,
            "user_email": user_email
        })
        print(f"✅ Deleted {chunks_result.deleted_count} chunks")
        
        # 3. Delete all chat sessions for this bot
        sessions = await database.chat_sessions.find({
            "textbook_id": bot_id,
            "user_email": user_email
        }).to_list(length=None)
        
        # 4. Delete all messages in those sessions
        total_messages_deleted = 0
        for session in sessions:
            messages_result = await database.chat_messages.delete_many({
                "session_id": session["_id"]
            })
            total_messages_deleted += messages_result.deleted_count
        
        print(f"✅ Deleted {total_messages_deleted} messages")
        
        # 5. Delete chat sessions
        sessions_result = await database.chat_sessions.delete_many({
            "textbook_id": bot_id,
            "user_email": user_email
        })
        print(f"✅ Deleted {sessions_result.deleted_count} sessions")
        
        # 6. Delete vector embeddings (FAISS files)
        from app.utils.vector_processor import delete_textbook_vectors
        vectors_deleted = delete_textbook_vectors(user_email, bot_id)
        print(f"✅ Deleted vector embeddings: {vectors_deleted}")
        
        # 7. Delete PDF file
        pdf_path = f"uploads/{user_email}/{bot_id}.pdf"
        pdf_deleted = False
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            pdf_deleted = True
            print(f"✅ Deleted PDF: {pdf_path}")
        
        print(f"🎉 Bot '{bot_name}' deleted successfully!")
        
        return {
            "success": True,
            "message": f"Bot '{bot_name}' deleted successfully",
            "bot_id": bot_id,
            "deleted": {
                "chunks": chunks_result.deleted_count,
                "sessions": sessions_result.deleted_count,
                "messages": total_messages_deleted,
                "vectors": vectors_deleted,
                "pdf_file": pdf_deleted
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting bot: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete bot: {str(e)}")