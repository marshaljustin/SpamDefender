from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer
from config import settings
import hashlib

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# Session serialization
session_serializer = URLSafeTimedSerializer(settings.SESSION_SECRET)

def create_session_token(data: dict):
    return session_serializer.dumps(data)

def verify_session_token(token: str, max_age=14*24*60*60):
    try:
        return session_serializer.loads(token, max_age=max_age)
    except:
        return None

# SHA256 hashing
def sha256_hash(data: str):
    return hashlib.sha256(data.encode()).hexdigest()