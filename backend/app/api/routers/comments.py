from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_comment_service, CurrentUser
from app.services.comment_service import CommentService
from app.services.exceptions import NotFoundError, ForbiddenError
from app.schemas.comment import CommentCreate, CommentOut

router = APIRouter(prefix="/tickets", tags=["comments"])
SvcDep = Annotated[CommentService, Depends(get_comment_service)]


@router.post("/{ticket_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(ticket_id: int, payload: CommentCreate, user: CurrentUser, svc: SvcDep):
    try:
        return svc.add_comment(user, ticket_id, payload.body)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/{ticket_id}/comments", response_model=list[CommentOut])
def list_comments(ticket_id: int, user: CurrentUser, svc: SvcDep):
    try:
        return svc.list_comments(user, ticket_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
