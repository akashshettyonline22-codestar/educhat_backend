from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.security import HTTPBearer
from app.database import database
from datetime import datetime

router = APIRouter(prefix="/analytics", tags=["Analytics"])
security = HTTPBearer()


@router.get("/")
async def get_analytics(
    request: Request,
    token: str = Depends(security)
):
    """Get complete analytics dashboard data"""
    user_email = request.state.current_user_email
    
    try:
        print(f"📊 Fetching analytics for: {user_email}")
        
        # GET USER NAME from users collection
        user = await database.users.find_one({"email": user_email})
        user_name = user.get("name", "User") if user else "User"
        
        # 1. COUNT TOTAL BOTS (unique textbooks)
        total_bots = await database.textbook_chunks.aggregate([
            {"$match": {"user_email": user_email}},
            {"$group": {"_id": "$textbook_id"}},
            {"$count": "total"}
        ]).to_list(length=1)
        
        num_bots = total_bots[0]["total"] if total_bots else 0
        
        # 2. COUNT STUDY MATERIALS (same as bots - each textbook is a study material)
        num_study_materials = num_bots
        
        # 3. COUNT USERS (for now, just 1 - the current user)
        num_users = 1
        
        # 4. COUNT TOTAL CONVERSATIONS (chat sessions)
        num_conversations = await database.chat_sessions.count_documents({
            "user_email": user_email
        })
        
        # 5. GET RECENT 4 BOTS
        recent_bots = await database.textbook_chunks.aggregate([
            {"$match": {"user_email": user_email}},
            {"$group": {
                "_id": "$textbook_id",
                "bot_name": {"$first": "$textbook_name"},
                "subject": {"$first": "$subject"},
                "grade": {"$first": "$grade"},
                "description": {"$first": "$description"},
                "created_at": {"$first": "$created_at"}
            }},
            {"$sort": {"created_at": -1}},
            {"$limit": 4}
        ]).to_list(length=4)
        
        # Format recent bots
        recent_bots_list = [
            {
                "bot_id": bot["_id"],
                "bot_name": bot["bot_name"],
                "subject": bot["subject"],
                "grade": bot["grade"],
                "description": bot.get("description", ""),
                "created_at": bot["created_at"]
            }
            for bot in recent_bots
        ]
        
        print(f"✅ Analytics fetched successfully for {user_name}")
        
        return {
            "success": True,
            "user_name": user_name,
            "analytics": {
                "total_bots": num_bots,
                "total_study_materials": num_study_materials,
                "total_users": num_users,
                "total_conversations": num_conversations
            },
            "recent_bots": recent_bots_list
        }
        
    except Exception as e:
        print(f"❌ Error fetching analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")
