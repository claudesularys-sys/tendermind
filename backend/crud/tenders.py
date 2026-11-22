import uuid
from datetime import date, datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from models.tender import Tender, TenderMatch, Favorite, CrawlerRun
from crawler.base import TenderCreate


async def get_tender_by_external_id(db: AsyncSession, external_id: str) -> Tender | None:
    result = await db.execute(select(Tender).where(Tender.external_id == external_id))
    return result.scalar_one_or_none()


async def create_tender(db: AsyncSession, data: TenderCreate) -> Tender:
    tender = Tender(
        external_id=data.external_id,
        source_id=data.source_id,
        country_code=data.country_code,
        country_name=data.country_name,
        city=data.city,
        title=data.title,
        title_en=data.title_en,
        equipment_summary=data.equipment_summary,
        description=data.description,
        budget_usd=data.budget_usd,
        currency_original=data.currency_original,
        budget_original=data.budget_original,
        deadline=data.deadline,
        url=data.url,
        raw_data=data.raw_data,
        is_active=True,
    )
    db.add(tender)
    await db.flush()
    return tender


async def get_active_matches(
    db: AsyncSession,
    user_id: uuid.UUID,
    country_code: str | None = None,
    source_id: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[tuple[Tender, TenderMatch]], int]:
    query = (
        select(Tender, TenderMatch)
        .join(TenderMatch, TenderMatch.tender_id == Tender.id)
        .where(
            TenderMatch.user_id == user_id,
            TenderMatch.ai_confirmed == True,
            Tender.is_active == True,
            Tender.deadline >= date.today(),
        )
    )
    if country_code:
        query = query.where(Tender.country_code == country_code)
    if source_id:
        query = query.where(Tender.source_id == source_id)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    query = query.order_by(Tender.deadline.asc()).offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(query)).all()
    return rows, total


async def deactivate_expired(db: AsyncSession) -> int:
    result = await db.execute(
        update(Tender)
        .where(Tender.deadline < date.today(), Tender.is_active == True)
        .values(is_active=False)
    )
    return result.rowcount


async def save_tender_match(
    db: AsyncSession,
    tender_id: uuid.UUID,
    user_id: uuid.UUID,
    vector_score: float,
    ai_confirmed: bool,
) -> TenderMatch:
    match = TenderMatch(
        tender_id=tender_id,
        user_id=user_id,
        vector_score=vector_score,
        ai_confirmed=ai_confirmed,
    )
    db.add(match)
    await db.flush()
    return match


async def mark_notified(db: AsyncSession, match_id: uuid.UUID, channel: str):
    result = await db.execute(select(TenderMatch).where(TenderMatch.id == match_id))
    match = result.scalar_one_or_none()
    if match:
        channels = list(match.notified_via or [])
        channels.append(channel)
        match.notified_via = channels
        match.notified_at = datetime.now(UTC)


async def get_match(db: AsyncSession, tender_id: uuid.UUID, user_id: uuid.UUID) -> TenderMatch | None:
    result = await db.execute(
        select(TenderMatch).where(
            TenderMatch.tender_id == tender_id,
            TenderMatch.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def toggle_favorite(db: AsyncSession, user_id: uuid.UUID, tender_id: uuid.UUID, note: str | None = None):
    result = await db.execute(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.tender_id == tender_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        return None
    fav = Favorite(user_id=user_id, tender_id=tender_id, note=note)
    db.add(fav)
    await db.flush()
    return fav


async def get_favorites(db: AsyncSession, user_id: uuid.UUID) -> list[tuple[Favorite, Tender]]:
    result = await db.execute(
        select(Favorite, Tender)
        .join(Tender, Tender.id == Favorite.tender_id)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.saved_at.desc())
    )
    return result.all()


async def log_crawler_run(db: AsyncSession, run_data: dict) -> CrawlerRun:
    run = CrawlerRun(**run_data)
    db.add(run)
    await db.flush()
    return run


async def get_latest_runs(db: AsyncSession) -> list[CrawlerRun]:
    subq = (
        select(CrawlerRun.source_id, func.max(CrawlerRun.ran_at).label("max_ran_at"))
        .group_by(CrawlerRun.source_id)
        .subquery()
    )
    result = await db.execute(
        select(CrawlerRun).join(
            subq,
            and_(
                CrawlerRun.source_id == subq.c.source_id,
                CrawlerRun.ran_at == subq.c.max_ran_at,
            ),
        )
    )
    return result.scalars().all()


async def get_map_data(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Tender.country_code, Tender.country_name, func.count(Tender.id).label("count"))
        .where(Tender.is_active == True)
        .group_by(Tender.country_code, Tender.country_name)
        .order_by(func.count(Tender.id).desc())
    )
    return [{"country_code": r.country_code, "country_name": r.country_name, "count": r.count} for r in result]
