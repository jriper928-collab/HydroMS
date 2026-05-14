"""Authentication business logic — register, login, token refresh, Google OAuth."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    CredentialsException,
    EmailAlreadyExistsException,
    InactiveUserException,
    UserNotFoundException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import (
    GoogleAuthRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)


async def register(db: AsyncSession, data: RegisterRequest) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise EmailAlreadyExistsException()

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token({"sub": user.id}),
        refresh_token=create_refresh_token({"sub": user.id}),
    )


async def login(db: AsyncSession, data: LoginRequest) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise CredentialsException()
    if not verify_password(data.password, user.hashed_password):
        raise CredentialsException()
    if not user.is_active:
        raise InactiveUserException()

    return TokenResponse(
        access_token=create_access_token({"sub": user.id}),
        refresh_token=create_refresh_token({"sub": user.id}),
    )


async def refresh(db: AsyncSession, data: RefreshRequest) -> TokenResponse:
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise CredentialsException(detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise UserNotFoundException()
    if not user.is_active:
        raise InactiveUserException()

    return TokenResponse(
        access_token=create_access_token({"sub": user.id}),
        refresh_token=create_refresh_token({"sub": user.id}),
    )


async def google_auth(db: AsyncSession, data: GoogleAuthRequest) -> TokenResponse:
    from google.auth.transport.requests import Request
    from google.oauth2 import id_token as google_id_token

    from app.config import settings

    try:
        info = google_id_token.verify_oauth2_token(
            data.id_token,
            Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise CredentialsException(detail="Invalid Google ID token")

    google_id = info["sub"]
    email = info["email"]
    full_name = info.get("name", email.split("@")[0])

    result = await db.execute(
        select(User).where(
            (User.google_id == google_id) | (User.email == email)
        )
    )
    user = result.scalar_one_or_none()

    if user:
        if not user.google_id:
            user.google_id = google_id
            await db.flush()
    else:
        user = User(
            email=email,
            full_name=full_name,
            google_id=google_id,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token({"sub": user.id}),
        refresh_token=create_refresh_token({"sub": user.id}),
    )
