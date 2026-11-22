import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import User, CompanyProfile
from core.security import hash_password, verify_password


async def create_user(db: AsyncSession, email: str, password: str) -> User:
    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    await db.flush()
    # Create empty profile
    profile = CompanyProfile(user_id=user.id)
    db.add(profile)
    await db.flush()
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str | uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    if user and verify_password(password, user.password_hash):
        return user
    return None


async def get_profile(db: AsyncSession, user_id: uuid.UUID) -> CompanyProfile | None:
    result = await db.execute(
        select(CompanyProfile).where(CompanyProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def upsert_profile(db: AsyncSession, user_id: uuid.UUID, data: dict) -> CompanyProfile:
    profile = await get_profile(db, user_id)
    if profile is None:
        profile = CompanyProfile(user_id=user_id, **data)
        db.add(profile)
    else:
        for key, value in data.items():
            setattr(profile, key, value)
    await db.flush()
    return profile


async def link_telegram(db: AsyncSession, user_id: uuid.UUID, telegram_id: int, chat_id: int) -> User | None:
    user = await get_user_by_id(db, user_id)
    if user:
        user.telegram_id = telegram_id
        user.telegram_chat_id = chat_id
        await db.flush()
    return user
