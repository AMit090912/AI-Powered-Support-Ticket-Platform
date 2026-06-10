from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_auth_service, CurrentUser
from app.services.auth_service import AuthService
from app.services.exceptions import ConflictError, NotFoundError
from app.schemas.auth import RegisterRequest, LoginRequest, Token, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
AuthDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, svc: AuthDep):
    try:
        return svc.register(payload.email, payload.password, payload.full_name, payload.role)
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, svc: AuthDep):
    try:
        user = svc.authenticate(payload.email, payload.password)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return Token(access_token=svc.issue_token(user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user
