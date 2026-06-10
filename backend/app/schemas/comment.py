from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.auth import UserOut


class CommentCreate(BaseModel):
    body: str = Field(min_length=1)


class CommentOut(BaseModel):
    id: int
    ticket_id: int
    body: str
    created_at: datetime
    author: UserOut

    model_config = {"from_attributes": True}
