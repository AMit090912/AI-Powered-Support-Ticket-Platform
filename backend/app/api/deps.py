from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.core import security
from app.models.user import User
from app.models.enums import Role
from app.repositories.user_repo import UserRepository
from app.repositories.ticket_repo import TicketRepository
from app.repositories.comment_repo import CommentRepository
from app.repositories.activity_repo import ActivityRepository
from app.services.auth_service import AuthService
from app.services.ticket_service import TicketService
from app.services.comment_service import CommentService
from app.services.analytics_service import AnalyticsService
from app.ai.factory import get_triage_provider, SafeTriageProvider

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

DbDep = Annotated[Session, Depends(get_db)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbDep) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = security.decode_token(token)
    if not payload or "sub" not in payload:
        raise cred_exc
    user = UserRepository(db).get(int(payload["sub"]))
    if not user:
        raise cred_exc
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_agent(user: CurrentUser) -> User:
    if user.role != Role.agent:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent role required")
    return user


AgentUser = Annotated[User, Depends(require_agent)]


# --- service factories ---
def get_auth_service(db: DbDep) -> AuthService:
    return AuthService(UserRepository(db))


def get_ticket_service(db: DbDep) -> TicketService:
    settings = get_settings()
    provider = SafeTriageProvider(
        get_triage_provider(settings.gemini_api_key, settings.gemini_model)
    )
    return TicketService(
        tickets=TicketRepository(db),
        activity=ActivityRepository(db),
        users=UserRepository(db),
        triage=provider,
    )


def get_comment_service(db: DbDep) -> CommentService:
    return CommentService(
        tickets=TicketRepository(db),
        comments=CommentRepository(db),
        activity=ActivityRepository(db),
    )


def get_analytics_service(db: DbDep) -> AnalyticsService:
    return AnalyticsService(TicketRepository(db))
