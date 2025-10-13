from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.routers.auth_router import router as auth_router

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request, exc):
    messages = []
    for err in exc.errors():
        if err.get('msg'):
            messages.append(err['msg'])
    return JSONResponse(
        status_code=400,
        content={"detail": ", ".join(messages)}
    )

@app.get("/")
def read_root():
    return {"message": "Welcome to EduChat backend!"}

app.include_router(auth_router)
