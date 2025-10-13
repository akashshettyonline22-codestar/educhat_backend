from app.database import database

async def find_user_by_email(email: str):
    return await database.users.find_one({"email": email})

async def create_user(user_data: dict):
    return await database.users.insert_one(user_data)
