from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "educhat_db"

client = AsyncIOMotorClient(MONGODB_URL)
database = client[DATABASE_NAME]
