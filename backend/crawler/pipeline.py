"""
Tender processing pipeline:
  TenderCreate list → deadline check → dedup → keyword filter
  → save to DB → embed → vector match → Claude quick check
  → save TenderMatch → Telegram alert

All matching runs via asyncio.gather() so it completes before returning —
safe for both FastAPI endpoints and Celery workers.
"""
import asyncio
import uuid
from datetime import date, datetime, UTC

from core.database import AsyncSessionLocal
from crud.tenders import get_tender_by_external_id, create_tender, save_tender_match, get_match, mark_notified
from crud.users import get_profile
from ai.analyzer import keyword_prefilter, quick_check
from .base import TenderCreate, CrawlResult


async def process_tenders(tenders: list[TenderCreate], result: CrawlResult) -> CrawlResult:
    """
    Process a batch of tenders:
    1. Filter expired + duplicates + keyword mismatch
    2. Save new ones to DB
    3. Run AI matching concurrently for all new tenders
    """
    match_coros = []

    async with AsyncSessionLocal() as db:
        for t in tenders:
            if t.deadline < date.today():
                continue
            if await get_tender_by_external_id(db, t.external_id):
                continue
            if not keyword_prefilter(t.title, t.description):
                continue

            tender = await create_tender(db, t)
            result.new_tenders += 1
            await db.commit()

            match_coros.append(_match_and_alert(str(tender.id), t))

    # Run all AI matching concurrently and wait for completion
    # (asyncio.gather ensures everything finishes before returning — safe for Celery)
    if match_coros:
        outcomes = await asyncio.gather(*match_coros, return_exceptions=True)
        result.matched = sum(1 for o in outcomes if o is True)
        for i, outcome in enumerate(outcomes):
            if isinstance(outcome, Exception):
                print(f"[pipeline] Match task {i} failed: {outcome}")

    return result


async def _match_and_alert(tender_db_id: str, t: TenderCreate) -> bool:
    """
    Embed tender → vector match → Claude check → save match → alert.
    Returns True if the tender was matched and alert sent.
    """
    tender_uuid = uuid.UUID(tender_db_id)

    # 1. Embed and get matching profiles
    try:
        from ai.embedder import embed_text, score_tender_against_profiles
        text = f"{t.title}. {t.description or ''}".strip()
        tender_vector = await embed_text(text)
        matched_profiles = await score_tender_against_profiles(tender_vector)
    except Exception as e:
        print(f"[pipeline] Embedding failed for {t.external_id}: {e}")
        matched_profiles = await _all_users_with_profiles()

    any_matched = False

    async with AsyncSessionLocal() as db:
        for user_id_str, score in matched_profiles:
            user_id = uuid.UUID(user_id_str)

            profile = await get_profile(db, user_id)
            if not profile:
                continue

            if await get_match(db, tender_uuid, user_id):
                continue

            # 2. Claude quick check
            profile_dict = {
                "company_name": profile.company_name,
                "transformer_types": profile.transformer_types,
                "power_kva_min": profile.power_kva_min,
                "power_kva_max": profile.power_kva_max,
                "voltage_kv": profile.voltage_kv,
                "keywords_extra": profile.keywords_extra,
            }
            is_match, equipment_summary = await quick_check(t.title, t.description, None, profile_dict)
            if not is_match:
                continue

            # 3. Save match
            match = await save_tender_match(db, tender_uuid, user_id, score, ai_confirmed=True)

            # 4. Update equipment_summary on the tender row
            if equipment_summary:
                from sqlalchemy import select
                from models.tender import Tender
                res = await db.execute(select(Tender).where(Tender.id == tender_uuid))
                row = res.scalar_one_or_none()
                if row:
                    row.equipment_summary = equipment_summary

            await db.commit()

            # 5. Send Telegram alert
            from models.user import User
            from sqlalchemy import select
            res = await db.execute(select(User).where(User.id == user_id))
            user = res.scalar_one_or_none()
            if user and user.telegram_chat_id and user.notif_enabled:
                try:
                    from bot.sender import send_tender_alert
                    await send_tender_alert(user.telegram_chat_id, t, equipment_summary)
                    await mark_notified(db, match.id, "telegram")
                    await db.commit()
                except Exception as e:
                    print(f"[pipeline] Telegram alert failed for chat {user.telegram_chat_id}: {e}")

            any_matched = True

    return any_matched


async def _all_users_with_profiles() -> list[tuple[str, float]]:
    """Fallback when embedding is unavailable: return all users with profiles."""
    from sqlalchemy import select
    from models.user import CompanyProfile
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(CompanyProfile.user_id))
        return [(str(row[0]), 0.0) for row in result.all()]


async def expire_old_tenders() -> int:
    """Deactivate tenders whose deadline has passed. Called by Celery beat."""
    async with AsyncSessionLocal() as db:
        from crud.tenders import deactivate_expired
        count = await deactivate_expired(db)
        await db.commit()
    if count:
        print(f"[expiry] Deactivated {count} expired tenders")
    return count
