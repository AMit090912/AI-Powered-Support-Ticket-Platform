from typing import Annotated
from fastapi import APIRouter, Depends

from app.api.deps import AgentUser, DbDep, CurrentUser, get_ticket_service
from app.repositories.user_repo import UserRepository
from app.repositories.activity_repo import ActivityRepository
from app.services.ticket_service import TicketService
from app.schemas.auth import UserOut
from app.schemas.activity import ActivityOut

router = APIRouter(tags=["users"])


@router.get("/users/agents", response_model=list[UserOut])
def list_agents(_: AgentUser, db: DbDep):
    return UserRepository(db).list_agents()


@router.get("/tickets/{ticket_id}/activity", response_model=list[ActivityOut])
def ticket_activity(
    ticket_id: int,
    user: CurrentUser,
    db: DbDep,
    svc: Annotated[TicketService, Depends(get_ticket_service)],
):
    # Reuse ticket access check (raises NotFoundError/ForbiddenError -> handled by global handlers).
    svc.get_ticket(user, ticket_id)
    return ActivityRepository(db).list_for_ticket(ticket_id)
