from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.routers.auth_router import router as auth_router
from app.middleware.auth_middleware import JWTAuthMiddleware
from app.routers.textbook_router import router as textbook_router
from app.utils.vector_processor import search_similar_chunks
from fastapi.security import HTTPBearer
from app.routers.qa_router import router as qa_router

app = FastAPI()

security = HTTPBearer()
# Add CORS middleware - ADD THIS SECTION
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or ["*"] to allow all origins (for development only!)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(JWTAuthMiddleware)

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

@app.get("/")
def read_root():
    return {"message": "Welcome to EduChat backend!"}


app.include_router(auth_router)
app.include_router(textbook_router)
app.include_router(qa_router)
