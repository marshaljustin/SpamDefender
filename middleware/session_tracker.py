from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from database import sessions_collection
from utils.security import create_session_token, verify_session_token
from config import settings


class SessionTrackerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get session ID from cookie
        session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
        request.state.session = None

        if session_id:
            # Verify session token
            session_data = verify_session_token(session_id)
            if session_data:
                # Get session from database
                session = await sessions_collection.find_one({"session_id": session_data.get("session_id")})
                if session:
                    request.state.session = session

        response = await call_next(request)

        # Set session cookie if needed
        if hasattr(request.state, "new_session") and request.state.new_session:
            response.set_cookie(
                key=settings.SESSION_COOKIE_NAME,
                value=create_session_token(request.state.new_session),
                httponly=settings.SESSION_COOKIE_HTTPONLY,
                secure=settings.SESSION_COOKIE_SECURE,
                samesite=settings.SESSION_COOKIE_SAMESITE,
                max_age=settings.SESSION_EXPIRE_DAYS * 24 * 60 * 60
            )

        return response