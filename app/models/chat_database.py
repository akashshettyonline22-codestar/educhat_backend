import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.database import database
from app.schemas.chat_schemas import MessageType, SessionStatus


# CHAT SESSION DATABASE OPERATIONS

async def create_chat_session_db(user_email: str, textbook_id: str, session_name: str = None) -> str:
    """Create a new chat session in database"""
    
    session_id = str(uuid.uuid4())
    
    # Auto-generate session name if not provided
    if not session_name:
        textbook_info = await get_textbook_info_for_session(user_email, textbook_id)
        textbook_name = textbook_info.get("textbook_name", "Textbook") if textbook_info else "Textbook"
        session_name = f"{textbook_name} - {datetime.now().strftime('%m/%d %H:%M')}"
    
    session_document = {
        "_id": session_id,
        "user_email": user_email,
        "textbook_id": textbook_id,
        "session_name": session_name,
        "created_at": datetime.utcnow(),
        "last_active": datetime.utcnow(),
        "message_count": 0,
        "status": SessionStatus.ACTIVE
    }
    
    await database.chat_sessions.insert_one(session_document)
    print(f"Created chat session: {session_id}")
    
    return session_id


async def get_chat_session_db(session_id: str, user_email: str) -> Optional[Dict]:
    """Get chat session from database"""
    
    try:
        session = await database.chat_sessions.find_one({
            "_id": session_id,
            "user_email": user_email
        })
        
        return session
        
    except Exception as e:
        print(f"Error getting chat session: {e}")
        return None


async def update_session_activity_db(session_id: str) -> bool:
    """Update session last active timestamp"""
    
    try:
        result = await database.chat_sessions.update_one(
            {"_id": session_id},
            {
                "$set": {"last_active": datetime.utcnow()},
                "$inc": {"message_count": 1}
            }
        )
        
        return result.modified_count > 0
        
    except Exception as e:
        print(f"Error updating session activity: {e}")
        return False


async def get_user_chat_sessions_db(user_email: str, limit: int = 20) -> List[Dict]:
    """Get user's chat sessions from database"""
    
    try:
        sessions = await database.chat_sessions.find({
            "user_email": user_email
        }).sort("last_active", -1).limit(limit).to_list(length=None)
        
        # Add preview message for each session
        for session in sessions:
            preview = await get_session_preview_message(session["_id"], user_email)
            session["preview_message"] = preview
        
        return sessions
        
    except Exception as e:
        print(f"Error getting user chat sessions: {e}")
        return []


async def delete_chat_session_db(session_id: str, user_email: str) -> bool:
    """Delete chat session and all its messages"""
    
    try:
        # Delete all messages in the session
        await database.chat_messages.delete_many({
            "session_id": session_id,
            "user_email": user_email
        })
        
        # Delete the session
        result = await database.chat_sessions.delete_one({
            "_id": session_id,
            "user_email": user_email
        })
        
        return result.deleted_count > 0
        
    except Exception as e:
        print(f"Error deleting chat session: {e}")
        return False


# CHAT MESSAGE DATABASE OPERATIONS

async def save_chat_message_db(
    session_id: str,
    user_email: str, 
    message_type: MessageType,
    content: str,
    metadata: Dict[str, Any] = None
) -> str:
    """Save chat message to database"""
    
    message_id = str(uuid.uuid4())
    
    message_document = {
        "_id": message_id,
        "session_id": session_id,
        "user_email": user_email,
        "message_type": message_type.value,
        "content": content,
        "timestamp": datetime.utcnow(),
        "metadata": metadata or {}
    }
    
    # Save message
    await database.chat_messages.insert_one(message_document)
    
    # Update session activity
    await update_session_activity_db(session_id)
    
    print(f"Saved {message_type.value} message: {message_id}")
    
    return message_id


async def get_chat_messages_db(
    session_id: str, 
    user_email: str, 
    limit: int = 50,
    skip: int = 0
) -> List[Dict]:
    """Get chat messages from database"""
    
    try:
        messages = await database.chat_messages.find({
            "session_id": session_id,
            "user_email": user_email
        }).sort("timestamp", 1).skip(skip).limit(limit).to_list(length=None)
        
        return messages
        
    except Exception as e:
        print(f"Error getting chat messages: {e}")
        return []


async def get_recent_chat_messages_db(
    session_id: str,
    user_email: str,
    limit: int = 10
) -> List[Dict]:
    """Get recent chat messages for context (excluding current conversation)"""
    
    try:
        messages = await database.chat_messages.find({
            "session_id": session_id,
            "user_email": user_email
        }).sort("timestamp", -1).limit(limit).to_list(length=None)
        
        # Return in chronological order
        messages.reverse()
        
        return messages
        
    except Exception as e:
        print(f"Error getting recent chat messages: {e}")
        return []


async def delete_chat_message_db(message_id: str, user_email: str) -> bool:
    """Delete a specific chat message"""
    
    try:
        result = await database.chat_messages.delete_one({
            "_id": message_id,
            "user_email": user_email
        })
        
        return result.deleted_count > 0
        
    except Exception as e:
        print(f"Error deleting chat message: {e}")
        return False


async def get_session_message_count_db(session_id: str, user_email: str) -> int:
    """Get total message count for a session"""
    
    try:
        count = await database.chat_messages.count_documents({
            "session_id": session_id,
            "user_email": user_email
        })
        
        return count
        
    except Exception as e:
        print(f"Error getting message count: {e}")
        return 0


# HELPER FUNCTIONS

async def get_session_preview_message(session_id: str, user_email: str) -> str:
    """Get first user message as session preview"""
    
    try:
        first_message = await database.chat_messages.find_one({
            "session_id": session_id,
            "user_email": user_email,
            "message_type": MessageType.USER.value
        }, sort=[("timestamp", 1)])
        
        if first_message:
            content = first_message["content"]
            return content[:60] + "..." if len(content) > 60 else content
        
        return "New conversation"
        
    except Exception as e:
        print(f"Error getting preview message: {e}")
        return "New conversation"


async def get_textbook_info_for_session(user_email: str, textbook_id: str) -> Optional[Dict]:
    """Get textbook info for session naming"""
    
    try:
        chunk = await database.textbook_chunks.find_one({
            "textbook_id": textbook_id,
            "user_email": user_email
        })
        
        if chunk:
            return {
                "textbook_name": chunk.get("textbook_name", "Textbook"),
                "subject": chunk.get("subject", ""),
                "grade": chunk.get("grade", "")
            }
        
        return None
        
    except Exception as e:
        print(f"Error getting textbook info: {e}")
        return None


async def cleanup_old_sessions(user_email: str, days_old: int = 30) -> int:
    """Clean up old inactive sessions (optional maintenance function)"""
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Find old sessions
        old_sessions = await database.chat_sessions.find({
            "user_email": user_email,
            "last_active": {"$lt": cutoff_date}
        }).to_list(length=None)
        
        deleted_count = 0
        
        for session in old_sessions:
            session_id = session["_id"]
            
            # Delete messages
            await database.chat_messages.delete_many({
                "session_id": session_id,
                "user_email": user_email
            })
            
            # Delete session
            await database.chat_sessions.delete_one({
                "_id": session_id
            })
            
            deleted_count += 1
        
        print(f"Cleaned up {deleted_count} old sessions")
        return deleted_count
        
    except Exception as e:
        print(f"Error cleaning up old sessions: {e}")
        return 0


# DATABASE INDEXES (Call this once to setup indexes)

async def create_chat_indexes():
    """Create database indexes for optimal chat performance"""
    
    try:
        # Chat sessions indexes
        await database.chat_sessions.create_index([
            ("user_email", 1),
            ("last_active", -1)
        ])
        
        await database.chat_sessions.create_index([
            ("user_email", 1),
            ("textbook_id", 1)
        ])
        
        # Chat messages indexes
        await database.chat_messages.create_index([
            ("session_id", 1),
            ("timestamp", 1)
        ])
        
        await database.chat_messages.create_index([
            ("user_email", 1),
            ("session_id", 1),
            ("timestamp", -1)
        ])
        
        await database.chat_messages.create_index([
            ("session_id", 1),
            ("message_type", 1),
            ("timestamp", 1)
        ])
        
        print("✅ Chat database indexes created successfully")
        
    except Exception as e:
        print(f"Error creating chat indexes: {e}")
