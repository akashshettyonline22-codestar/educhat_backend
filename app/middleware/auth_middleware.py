from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.auth_utils import verify_token
import json

class JWTAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, public_paths=None):
        super().__init__(app)
        # Define paths that don't need authentication
        self.public_paths = public_paths or [
            "/", 
            "/docs", 
            "/openapi.json", 
            "/redoc",
            "/register", 
            "/login",
            "/qa/images"
        ]

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/qa/images"):
           print("hello")
           response= await call_next(request)
           return response
        # Skip authentication for public paths
        print("inside middleware")
        if request.url.path in self.public_paths:
            response = await call_next(request)
            return response
        
        # Check for Authorization header
        print(request.body)
        auth_header = request.headers.get("Authorization")
        print(f"Authorization header: {auth_header}")
        
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization header missing"},
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Extract token from "Bearer <token>"
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid authorization header format"},
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        token = auth_header.split(" ")[1]
        
        # Verify the JWT token
        payload = verify_token(token)
        if not payload:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Add user info to request state for later use
        request.state.current_user_email = payload.get("email")
        request.state.token_payload = payload
        
        # Continue to the endpoint
        response = await call_next(request)
        return response

def decode_token_simple(token: str) -> str or None:
        """
        Decode JWT token and extract email (returns None on error)
        Use this for Socket.IO where you can't raise HTTPException
        
        Args:
            token (str): JWT token string
        
        Returns:
            str or None: User email if valid, None if invalid
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith("Bearer "):
                token = token.split(" ")[1]
            
            # Verify token
            payload = verify_token(token)
            
            if not payload:
                return None
            
            # Extract email
            email = payload.get("email") or payload.get("sub")
            return email
            
        except Exception as e:
            print(f"❌ Token decode error: {e}")
            return None