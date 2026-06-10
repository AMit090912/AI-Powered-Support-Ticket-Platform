from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.models.enums import Role


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=1)
    role: Role = Role.customer


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: Role
    created_at: datetime

    model_config = {"from_attributes": True}
