from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, CollectionInvalid
from fastapi import Depends

MONGO_URL = "mongodb+srv://25917021:by3rANvSi3bC8PIw@pwnedproject.yfx9bzf.mongodb.net/"
DB_NAME = "pwned_db"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

async def connect_to_mongo():
    try:
        await client.admin.command('ping')
        await db.uploads.create_index("user_id")
        await db.uploads.create_index("processing_status")
        await db.breaches.create_index("DataClasses")
        await db.users.create_index("email", unique=True)
        
        if "password_resets" not in await db.list_collection_names():
            await db.create_collection("password_resets")

        print("Successfully connected to MongoDB")
    except ConnectionFailure:
        print("Failed to connect to MongoDB")
        raise
    except CollectionInvalid:
        print("Failed to create collection")
        raise

async def close_mongo_connection():
    client.close()
    print("MongoDB connection closed")

# Dependency to get the MongoDB instance
async def get_db():
    return db