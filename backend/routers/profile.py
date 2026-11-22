import asyncio
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_user
from crud.users import get_profile, upsert_profile
from schemas.user import CompanyProfileIn, CompanyProfileOut
from models.user import User

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=CompanyProfileOut | None)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_profile(db, current_user.id)


@router.put("", response_model=CompanyProfileOut)
async def update_profile(
    body: CompanyProfileIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await upsert_profile(db, current_user.id, body.model_dump())

    # Extract plain data before the session closes (avoids DetachedInstanceError)
    profile_data = {
        "id": str(profile.id),
        "user_id": str(profile.user_id),
        "company_name": profile.company_name,
        "transformer_types": list(profile.transformer_types or []),
        "power_kva_min": profile.power_kva_min,
        "power_kva_max": profile.power_kva_max,
        "voltage_kv": list(profile.voltage_kv or []),
        "certifications": list(profile.certifications or []),
        "keywords_extra": list(profile.keywords_extra or []),
    }

    background_tasks.add_task(_re_embed_profile, profile_data)
    return profile


async def _re_embed_profile(profile_data: dict):
    """Re-embed the company profile in Qdrant after profile update."""
    try:
        from ai.embedder import embed_profile_dict
        await embed_profile_dict(profile_data)
    except Exception as e:
        print(f"[profile] Re-embedding failed: {e}")
