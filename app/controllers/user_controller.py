from datetime import datetime
from app.models.user_model import find_user_by_email, create_user
from app.security import hash_password

async def register_user(user):
    existing = await find_user_by_email(user.email)
    if existing:
        return {"error": "Email already registered"}
    user_doc = {
        "email": user.email,
        "username": user.username,
        "password": hash_password(user.password),
        "full_name": user.full_name,
        "created_at": datetime.utcnow(),
    }
    await create_user(user_doc)
    return {"message": "User registered successfully"}
