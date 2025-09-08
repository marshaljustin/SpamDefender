from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema, handler):
        field_schema.update(type="string")

class SessionInfo(BaseModel):
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    expired: bool = False

class User(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    email: str
    password: Optional[str] = None  
    google_id: Optional[str] = None
    google_tokens: Optional[dict] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    verified: bool = False
    created_at: datetime = datetime.utcnow()
    last_login: Optional[datetime] = None
    sessions: List[SessionInfo] = []

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime
    google_connected: bool

    model_config = ConfigDict(
        json_encoders={ObjectId: str}
    )
