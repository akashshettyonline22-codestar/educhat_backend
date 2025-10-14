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


from datetime import datetime
from app.models.user_model import find_user_by_email, create_user
from app.security import hash_password, verify_password
from app.auth_utils import create_access_token

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

# Add this new login function
async def login_user(user):
    existing_user = await find_user_by_email(user.email)
    if not existing_user:
        return {"error": "Invalid email or password"}
    
    if not verify_password(user.password, existing_user["password"]):
        return {"error": "Invalid email or password"}
    
    # Create JWT token
    access_token = create_access_token(data={"email": existing_user["email"]})
    
    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": existing_user["email"],
            "username": existing_user["username"],
            "full_name": existing_user["full_name"]
        }
    }
