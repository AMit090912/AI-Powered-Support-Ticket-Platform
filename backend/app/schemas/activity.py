from datetime import datetime
from pydantic import BaseModel
from app.models.enums import EventType
from app.schemas.auth import UserOut


class ActivityOut(BaseModel):
    id: int
    event_type: EventType
    old_value: str | None
    new_value: str | None
    created_at: datetime
    actor: UserOut | None

    model_config = {"from_attributes": True}
