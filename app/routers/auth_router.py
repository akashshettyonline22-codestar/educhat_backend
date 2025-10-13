from fastapi import APIRouter, HTTPException, Request
from app.schemas.user import UserSignup
from app.controllers.user_controller import register_user
from fastapi.responses import JSONResponse
from pydantic import ValidationError

router = APIRouter()

@router.post("/register")
async def register(user: UserSignup):
    result = await register_user(user)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result




