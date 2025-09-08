import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/email_scanner")
    SESSION_SECRET = os.getenv("SESSION_SECRET", "session-secret-key")

    # Email scanning configuration
    CREDENTIALS_FILE = "credentials.json"
    TOKEN_FILE = "token.pickle"
    MODEL_PATH = "model/spam_model_fixed.pkl"
    MAX_EMAILS = 30
    SCOPES = "your read url"

    # Session settings
    SESSION_COOKIE_NAME = "session_id"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = "lax"
    SESSION_EXPIRE_DAYS = 7


settings = Settings()