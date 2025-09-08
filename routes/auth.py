from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from datetime import datetime, timedelta
import uuid
from bson import ObjectId

from database import users_collection, sessions_collection
from models.user import UserCreate, UserLogin, UserResponse
from utils.security import verify_password, get_password_hash, create_session_token
from config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


async def get_current_user(request: Request):
    if not hasattr(request.state, 'session') or not request.state.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    user_id = request.state.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, request: Request):
    # Check if user already exists
    existing_user = await users_collection.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash password and create user
    hashed_password = get_password_hash(user_data.password)
    user_data_dict = {
        "email": user_data.email,
        "password": hashed_password,
        "created_at": datetime.utcnow(),
        "sessions": [],
        "google_connected": False
    }

    result = await users_collection.insert_one(user_data_dict)

    # Create session
    session_id = str(uuid.uuid4())
    session_token = create_session_token({
        "session_id": session_id,
        "user_id": str(result.inserted_id)
    })

    # Store session in database
    await sessions_collection.insert_one({
        "session_id": session_id,
        "user_id": result.inserted_id,
        "data": {"email": user_data.email},
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=settings.SESSION_EXPIRE_DAYS)
    })

    # Update user sessions
    session_info = {
        "session_id": session_id,
        "start_time": datetime.utcnow()
    }

    await users_collection.update_one(
        {"_id": result.inserted_id},
        {"$push": {"sessions": session_info}}
    )

    # Set session in request state for middleware to set cookie
    request.state.new_session = {
        "session_id": session_id,
        "user_id": str(result.inserted_id)
    }

    return UserResponse(
        id=str(result.inserted_id),
        email=user_data.email,
        created_at=user_data_dict["created_at"],
        google_connected=False
    )


@router.post("/login")
async def login(user_data: UserLogin, request: Request):
    # Find user
    user = await users_collection.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Close any expired sessions
    now = datetime.utcnow()
    expired_sessions = []

    if "sessions" in user:
        for session in user["sessions"]:
            if not session.get("end_time") and session["start_time"] < now - timedelta(
                    days=settings.SESSION_EXPIRE_DAYS):
                expired_sessions.append(session["session_id"])
                session["end_time"] = session["start_time"] + timedelta(days=settings.SESSION_EXPIRE_DAYS)
                session["duration"] = (session["end_time"] - session["start_time"]).total_seconds()
                session["expired"] = True

    if expired_sessions:
        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"sessions": user["sessions"]}}
        )

    # Create new session
    session_id = str(uuid.uuid4())
    session_token = create_session_token({
        "session_id": session_id,
        "user_id": str(user["_id"])
    })

    # Store session in database
    await sessions_collection.insert_one({
        "session_id": session_id,
        "user_id": user["_id"],
        "data": {"email": user["email"]},
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=settings.SESSION_EXPIRE_DAYS)
    })

    # Update user sessions
    session_info = {
        "session_id": session_id,
        "start_time": datetime.utcnow()
    }

    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$push": {"sessions": session_info}}
    )

    # Set session in request state for middleware to set cookie
    request.state.new_session = {
        "session_id": session_id,
        "user_id": str(user["_id"])
    }

    return {"message": "Login successful"}


@router.post("/logout")
async def logout(request: Request, response: Response):
    if hasattr(request.state, 'session') and request.state.session:
        session_id = request.state.session.get("session_id")

        # Remove session from database
        await sessions_collection.delete_one({"session_id": session_id})

        # Update user session end time
        user_id = request.state.session.get("user_id")
        if user_id:
            user = await users_collection.find_one({"_id": ObjectId(user_id)})
            if user and "sessions" in user:
                for session in user["sessions"]:
                    if session["session_id"] == session_id and not session.get("end_time"):
                        session["end_time"] = datetime.utcnow()
                        session["duration"] = (datetime.utcnow() - session["start_time"]).total_seconds()

                await users_collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"sessions": user["sessions"]}}
                )

    # Clear session cookie
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return {"message": "Logout successful"}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "email": current_user["email"],
        "google_connected": current_user.get("google_connected", False)
    }