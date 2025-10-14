import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from dotenv import load_dotenv,find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

def create_access_token(data: dict):
    print("Current working directory:", os.getcwd())
    print("SECRET_KEY:", os.getenv("SECRET_KEY"))
    print("ALGORITHM:", os.getenv("ALGORITHM"))
    print("SECRET_KEY",SECRET_KEY)
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
