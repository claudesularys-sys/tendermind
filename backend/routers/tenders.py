import uuid
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_user
from crud.tenders import get_active_matches, toggle_favorite, get_favorites
from schemas.tender import TenderOut, TenderListResponse, FavoriteOut
from models.user import User

router = APIRouter(prefix="/tenders", tags=["tenders"])


@router.get("", response_model=TenderListResponse)
async def list_tenders(
    country_code: str | None = Query(None),
    source_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows, total = await get_active_matches(
        db, current_user.id, country_code, source_id, page, per_page
    )
    items = []
    for tender, match in rows:
        t = TenderOut.model_validate(tender)
        t.vector_score = match.vector_score
        items.append(t)
    return TenderListResponse(items=items, total=total, page=page, per_page=per_page)


@router.post("/{tender_id}/save")
async def save_tender(
    tender_id: uuid.UUID,
    note: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await toggle_favorite(db, current_user.id, tender_id, note)
    return {"saved": result is not None}


@router.get("/favorites", response_model=list[FavoriteOut])
async def list_favorites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = await get_favorites(db, current_user.id)
    result = []
    for fav, tender in rows:
        result.append(FavoriteOut(
            id=fav.id,
            tender=TenderOut.model_validate(tender),
            note=fav.note,
            saved_at=fav.saved_at,
        ))
    return result
