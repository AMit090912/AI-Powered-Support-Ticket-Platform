from datetime import datetime
from pydantic import BaseModel, Field
from app.models.enums import Status, Priority, Category
from app.schemas.auth import UserOut


class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)


class TicketUpdate(BaseModel):
    status: Status | None = None
    priority: Priority | None = None
    category: Category | None = None
    assigned_to_id: int | None = None


class TicketOut(BaseModel):
    id: int
    title: str
    description: str
    status: Status
    priority: Priority
    category: Category
    suggested_response: str | None
    created_at: datetime
    updated_at: datetime
    created_by: UserOut
    assigned_to: UserOut | None

    model_config = {"from_attributes": True}


class PaginatedTickets(BaseModel):
    items: list[TicketOut]
    total: int
    page: int
    page_size: int
