from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer
import os

from app.routers.auth_router import router as auth_router
from app.middleware.auth_middleware import JWTAuthMiddleware
from app.routers.textbook_router import router as textbook_router
from app.utils.vector_processor import search_similar_chunks
from app.routers.qa_router import router as qa_router
from app.routers.bots_router import router as bots_router
from app.routers.analytics_router import router as analytics_router


from app.websocket.socket_manager import sio, get_socket_app
from pathlib import Path
# 1. Create app
app = FastAPI()
security = HTTPBearer()

project_root = Path(__file__).parent.parent
qa_images_path = os.path.join(project_root, "data", "educational_images")

print(f"📁 Static files path: {qa_images_path}")
print(f"📁 Path exists: {os.path.exists(qa_images_path)}")

os.makedirs(qa_images_path, exist_ok=True)  # Create if doesn't exist
app.mount("/qa/images", StaticFiles(directory=qa_images_path), name="qa_images")

# 3. Add CORS origins
origins = ["http://localhost:5173"]

# 4. Add middlewares (JWT first, then CORS)
app.add_middleware(JWTAuthMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Exception handler
@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request, exc):
    errors = []
    for err in exc.errors():
        if err.get('msg'):
            errors.append(err['msg'])
    return JSONResponse(
        status_code=400,
        content={"msg": ", ".join(errors)}
    )

# 6. Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to EduChat backend!"}

# 7. Include all routers
app.include_router(auth_router)
app.include_router(textbook_router)
app.include_router(qa_router)
app.include_router(bots_router)

app.include_router(analytics_router)

# 8. Wrap with Socket.IO LAST
app = get_socket_app(app)
