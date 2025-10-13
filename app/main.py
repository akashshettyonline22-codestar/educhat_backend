from fastapi import FastAPI
from app.routers.auth_router import router as auth_router

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Welcome to EduChat backend!"}

# Include the authentication routes
app.include_router(auth_router)
