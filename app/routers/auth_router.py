from fastapi import APIRouter, HTTPException
from app.schemas.user import UserSignup
from app.controllers.user_controller import register_user

router = APIRouter()

@router.post("/register")
async def register(user: UserSignup):
    result = await register_user(user)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
