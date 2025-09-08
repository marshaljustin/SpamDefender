from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from bson import ObjectId

client = AsyncIOMotorClient(settings.MONGO_URI)
database = client.email_scanner
users_collection = database.users
sessions_collection = database.sessions
email_scans_collection = database.email_scans

def user_helper(user) -> dict:
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "created_at": user["created_at"],
        "google_connected": user.get("google_connected", False),
    }