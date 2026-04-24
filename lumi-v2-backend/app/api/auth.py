from fastapi import APIRouter, Depends, status

from app.core.security import get_current_user
from app.schemas.auth import AuthResponse, AuthUser, LoginRequest, SignupRequest
from app.services.auth_service import login_user, signup_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/status")
def auth_status() -> dict[str, str]:
    return {"module": "auth", "status": "ready"}


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest) -> AuthResponse:
    response = signup_user(payload.email, payload.password)
    return AuthResponse(**response)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    response = login_user(payload.email, payload.password)
    return AuthResponse(**response)


@router.get("/me", response_model=AuthUser)
def get_me(current_user: dict[str, str | None] = Depends(get_current_user)) -> AuthUser:
    return AuthUser(**current_user)
