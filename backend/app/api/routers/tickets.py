from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_ticket_service, CurrentUser
from app.services.ticket_service import TicketService
from app.services.exceptions import NotFoundError, ForbiddenError
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketOut, PaginatedTickets
from app.models.enums import Status, Priority, Category

router = APIRouter(prefix="/tickets", tags=["tickets"])
SvcDep = Annotated[TicketService, Depends(get_ticket_service)]


def _raise(e: Exception):
    if isinstance(e, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    if isinstance(e, ForbiddenError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    raise e


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketCreate, user: CurrentUser, svc: SvcDep):
    return svc.create_ticket(user, payload.title, payload.description)


@router.get("", response_model=PaginatedTickets)
def list_tickets(
    user: CurrentUser,
    svc: SvcDep,
    q: str | None = None,
    status_: Status | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    category: Category | None = None,
    assignee_id: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    items, total = svc.list_tickets(
        user, q=q, status=status_, priority=priority, category=category,
        assignee_id=assignee_id, page=page, page_size=page_size,
    )
    return PaginatedTickets(items=items, total=total, page=page, page_size=page_size)


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, user: CurrentUser, svc: SvcDep):
    try:
        return svc.get_ticket(user, ticket_id)
    except (NotFoundError, ForbiddenError) as e:
        _raise(e)


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int, payload: TicketUpdate, user: CurrentUser, svc: SvcDep):
    try:
        return svc.update_ticket(user, ticket_id, payload.model_dump(exclude_unset=True))
    except (NotFoundError, ForbiddenError) as e:
        _raise(e)
