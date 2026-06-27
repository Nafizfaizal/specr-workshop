from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..database import get_db
from ..models import User
from ..schemas import Token, UserResponse, PasswordChange, LoginRequest
from ..auth import verify_password, hash_password, create_access_token, get_current_user
import uuid

router = APIRouter(tags=["auth"])


async def seed_default_admin(db: AsyncSession):
    """Create default superadmin if no users exist."""
    result = await db.execute(select(func.count()).select_from(User))
    count = result.scalar()
    if count == 0:
        admin = User(
            id=str(uuid.uuid4()),
            username="admin",
            name="Administrator",
            role="superadmin",
            password_hash=hash_password("admin123"),
            active=True,
        )
        db.add(admin)
        await db.commit()


async def _authenticate_user(username: str, password: str, db: AsyncSession) -> Token:
    await seed_default_admin(db)
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    token = create_access_token({"sub": user.id})
    return Token(access_token=token, token_type="bearer", user=UserResponse.model_validate(user))


@router.post("/auth/login", response_model=Token)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login with JSON body (username + password)."""
    return await _authenticate_user(body.username, body.password, db)


@router.post("/auth/token", response_model=Token)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """OAuth2 form-compatible login endpoint (for /docs Authorize button)."""
    return await _authenticate_user(form_data.username, form_data.password, db)


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/auth/me/password")
async def change_password(
    body: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"message": "Password updated successfully"}
