from fastapi import HTTPException, status
from loguru import logger

from app.integrations.supabase import get_supabase_client


def _extract_user_payload(user: object) -> dict[str, str | None]:
    user_id = getattr(user, "id", None)
    email = getattr(user, "email", None)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase returned user data without an id.",
        )

    return {
        "id": user_id,
        "email": email,
    }


def signup_user(email: str, password: str) -> dict[str, object]:
    client = get_supabase_client()

    try:
        response = client.auth.sign_up({"email": email, "password": password})
    except Exception as exc:
        logger.exception("Supabase signup failed for {}: {}", email, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signup failed. Check the email/password and try again.",
        ) from exc

    if not response or not response.user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signup failed. No user returned by Supabase.",
        )

    tokens = None
    message = "Signup successful."
    if response.session:
        tokens = {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": "bearer",
        }
    else:
        message = "Signup successful. Please verify your email before login."

    return {
        "user": _extract_user_payload(response.user),
        "tokens": tokens,
        "message": message,
    }


def login_user(email: str, password: str) -> dict[str, object]:
    client = get_supabase_client()

    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as exc:
        logger.exception("Supabase login failed for {}: {}", email, exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        ) from exc

    if not response or not response.user or not response.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login failed. Session not created.",
        )

    return {
        "user": _extract_user_payload(response.user),
        "tokens": {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": "bearer",
        },
        "message": "Login successful.",
    }


def get_user_from_jwt(token: str) -> dict[str, str | None]:
    client = get_supabase_client()

    try:
        response = client.auth.get_user(jwt=token)
    except Exception as exc:
        logger.warning("JWT verification failed: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        ) from exc

    if not response or not response.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    return _extract_user_payload(response.user)
