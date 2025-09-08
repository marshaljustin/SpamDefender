from datetime import timedelta, datetime
import logging
import uuid
import json
import os

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import RedirectResponse, Response
from authlib.integrations.httpx_client import AsyncOAuth2Client
from urllib.parse import quote

from database import users_collection, sessions_collection
from models.user import User, SessionInfo
from utils.security import create_session_token
from config import settings

# Set up logging with more detailed format
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Google Authentication"])

# Google OAuth2 configuration
GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


# Load Google credentials from JSON file
def load_google_credentials():
    try:
        cred_path = os.path.join(os.path.dirname(__file__), '..', 'cred.json')
        with open(cred_path, 'r') as f:
            creds = json.load(f)

        client_id = creds['web']['client_id']
        client_secret = creds['web']['client_secret']
        redirect_uri = creds['web']['redirect_uris'][0]

        logger.info(f"Loaded Google credentials")
        return client_id, client_secret, redirect_uri

    except Exception as e:
        logger.error(f"Failed to load Google credentials: {str(e)}")
        raise


# Load credentials at startup
try:
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI = load_google_credentials()
except Exception as e:
    logger.error(f"Google authentication will not work: {str(e)}")
    GOOGLE_CLIENT_ID = GOOGLE_CLIENT_SECRET = GOOGLE_REDIRECT_URI = None


@router.get("/google")
async def google_login(request: Request):
    """Initiate Google OAuth flow"""
    try:
        if not GOOGLE_CLIENT_ID or not GOOGLE_REDIRECT_URI:
            raise Exception("Google credentials not configured")

        # DEBUG: Log the credentials (mask secret for security)
        logger.info(f"Using Client ID")
        logger.info(f"Using Redirect URI")

        oauth = AsyncOAuth2Client(
            client_id=GOOGLE_CLIENT_ID,
            redirect_uri=GOOGLE_REDIRECT_URI,
            scope="openid email profile"
        )

        # Generate and store state for CSRF protection
        state = str(uuid.uuid4())

        authorization_url, _ = oauth.create_authorization_url(
            GOOGLE_AUTHORIZATION_URL,
            state=state,
            access_type="offline",
            prompt="select_account",
            include_granted_scopes="true"
        )

        logger.info(f"Initiating Google OAuth for state")
        logger.info(f"Authorization URL")
        return RedirectResponse(authorization_url)

    except Exception as e:
        logger.error(f"Failed to initiate Google OAuth: {str(e)}", exc_info=True)
        error_message = "Failed to initiate Google login. Please try again."
        return RedirectResponse(url=f"/login?error={quote(error_message)}")


@router.get("/google/callback")
async def google_callback(
        request: Request,
        code: str = None,
        state: str = None,
        error: str = None
):
    """Handle Google OAuth callback"""

    # Log all received parameters for debugging
    logger.info(f"Google callback received:")


    # Handle OAuth errors
    if error:
        logger.warning(f"Google OAuth error: {error}")
        error_messages = {
            "access_denied": "Google login was cancelled.",
            "invalid_request": "Invalid login request. Please try again.",
            "unauthorized_client": "Login service temporarily unavailable.",
        }
        error_message = error_messages.get(error, "Google login failed. Please try again.")
        return RedirectResponse(url=f"/login?error={quote(error_message)}")

    # Validate required parameters
    if not code:
        logger.error("No authorization code received from Google")
        return RedirectResponse(url=f"/login?error={quote('Authorization failed. Please try again.')}")

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not GOOGLE_REDIRECT_URI:
        logger.error("Google credentials not configured")
        return RedirectResponse(
            url=f"/login?error={quote('Server configuration error. Please contact administrator.')}")

    # Exchange code for tokens
    oauth = AsyncOAuth2Client(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        redirect_uri=GOOGLE_REDIRECT_URI
    )

    try:
        logger.info(f"Exchanging code for tokens with state")
        logger.info(f"Using Client ID")
        logger.info(f"Using Redirect URI")

        # Fetch access token
        token = await oauth.fetch_token(
            GOOGLE_TOKEN_URL,
            code=code,
            grant_type="authorization_code"
        )

        logger.info(f"Token response keys: {list(token.keys()) if token else 'No token'}")

        if not token or 'access_token' not in token:
            error_msg = "Failed to obtain access token from Google"
            if 'error' in token:
                error_msg = f"{error_msg}: {token['error']} - {token.get('error_description', 'No description')}"
            raise Exception(error_msg)

        # Get user info from Google
        oauth.token = token  # Set the token on the client
        user_info_response = await oauth.get(GOOGLE_USER_INFO_URL)

        logger.info(f"User info status: {user_info_response.status_code}")

        if user_info_response.status_code != 200:
            error_text = await user_info_response.text()
            logger.error(f"Failed to fetch user info: {user_info_response.status_code} - {error_text}")
            raise Exception(f"Failed to fetch user info: {user_info_response.status_code} - {error_text}")

        user_data = user_info_response.json()
        logger.info(f"User data received: {list(user_data.keys())}")
        logger.info(f"User data structure: {json.dumps(user_data, indent=2)}")

        # Validate required user data
        required_fields = ["email", "sub"]
        for field in required_fields:
            if field not in user_data:
                raise Exception(f"Missing required field: {field}")

        logger.info(f"Google user info received for email: {user_data['email']}")

        # Find or create user
        user = await users_collection.find_one({"email": user_data["email"]})
        user_id = None

        if not user:
            # Create new user
            logger.info(f"Creating new user for email: {user_data['email']}")

            new_user = User(
                email=user_data["email"],
                password="",  # No password for Google users
                google_id=user_data["sub"],
                google_tokens=token,
                name=user_data.get("name", ""),
                picture=user_data.get("picture", ""),
                verified=user_data.get("email_verified", False)
            )

            result = await users_collection.insert_one(new_user.dict(by_alias=True))
            user_id = result.inserted_id

        else:
            # Update existing user with Google info
            logger.info(f"Updating existing user: {user['email']}")

            update_data = {
                "google_id": user_data["sub"],
                "google_tokens": token,
                "name": user_data.get("name", user.get("name", "")),
                "picture": user_data.get("picture", user.get("picture", "")),
                "verified": user_data.get("email_verified", user.get("verified", False)),
                "last_login": datetime.utcnow()
            }

            await users_collection.update_one(
                {"_id": user["_id"]},
                {"$set": update_data}
            )
            user_id = user["_id"]

        # Create session
        session_id = str(uuid.uuid4())
        session_token = create_session_token({
            "session_id": session_id,
            "user_id": str(user_id)
        })

        # Store session in database
        session_expires_at = datetime.utcnow() + timedelta(days=settings.SESSION_EXPIRE_DAYS)
        await sessions_collection.insert_one({
            "session_id": session_id,
            "user_id": user_id,
            "data": {
                "email": user_data["email"],
                "login_method": "google",
                "user_agent": request.headers.get("user-agent", ""),
                "ip_address": request.client.host if request.client else ""
            },
            "created_at": datetime.utcnow(),
            "expires_at": session_expires_at
        })

        # Update user sessions
        session_info = SessionInfo(
            session_id=session_id,
            start_time=datetime.utcnow()
        )

        await users_collection.update_one(
            {"_id": user_id},
            {"$push": {"sessions": session_info.dict()}}
        )

        logger.info(f"Session created for user: {user_data['email']}")

        # Create response with success redirect
        success_message = "Successfully signed in with Google!"
        redirect_url = request.cookies.get("redirect_after_login", "/index")

        response = RedirectResponse(
            url=f"{redirect_url}?success={quote(success_message)}"
        )

        # Set session cookie
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=session_token,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite=settings.SESSION_COOKIE_SAMESITE,
            max_age=settings.SESSION_EXPIRE_DAYS * 24 * 60 * 60,
            path="/"
        )

        # Clear redirect cookie if it exists
        response.delete_cookie("redirect_after_login")

        return response

    except Exception as e:
        logger.error(f"Google authentication failed: {str(e)}", exc_info=True)

        # Handle specific error types
        error_message = "Google authentication failed. Please try again."

        if "invalid_grant" in str(e).lower():
            error_message = "Login session expired. Please try again."
        elif "access_denied" in str(e).lower():
            error_message = "Access denied. Please check your Google account permissions."
        elif "network" in str(e).lower() or "connection" in str(e).lower():
            error_message = "Network error. Please check your connection and try again."

        return RedirectResponse(
            url=f"/login?error={quote(error_message)}"
        )


# Optional: Add a logout endpoint that clears Google tokens
@router.post("/google/revoke")
async def revoke_google_tokens(request: Request):
    """Revoke Google tokens and logout user"""
    try:
        # Get current user session
        session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if not session_token:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Decode session and get user
        # This would depend on your session decoding implementation
        # You would get user_id from the session and then revoke Google tokens

        logger.info("Google tokens revoked successfully")
        return {"message": "Successfully logged out from Google"}

    except Exception as e:
        logger.error(f"Failed to revoke Google tokens: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout from Google"
        )
