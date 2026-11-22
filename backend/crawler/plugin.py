"""
TenderMind Plugin API
=====================

Adding a new tender source takes ~10-15 minutes:

  1. Create one file in backend/crawler/sources/<region>/<source_id>.py
  2. Inherit from BaseCrawler
  3. Implement fetch_tenders() → list[TenderCreate]
  4. Test: python -m crawler.cli test <source_id>
  5. Done — auto-discovered on next restart

See: backend/crawler/sources/_template.py for a fully-annotated example.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import NamedTuple

from .base import BaseCrawler, TenderCreate


# ── Validation ────────────────────────────────────────────────────────────────

class ValidationError(NamedTuple):
    field: str
    message: str


def validate_tender(t: TenderCreate) -> list[ValidationError]:
    """
    Validate a TenderCreate object before it enters the pipeline.
    Returns a list of errors; empty list means valid.
    """
    errors: list[ValidationError] = []

    if not t.external_id:
        errors.append(ValidationError("external_id", "required"))
    elif len(t.external_id) > 200:
        errors.append(ValidationError("external_id", "too long (max 200 chars)"))

    if not t.title:
        errors.append(ValidationError("title", "required"))
    elif len(t.title) > 500:
        errors.append(ValidationError("title", f"too long ({len(t.title)} > 500 chars)"))

    if not t.url:
        errors.append(ValidationError("url", "required"))
    elif not t.url.startswith("http"):
        errors.append(ValidationError("url", "must start with http:// or https://"))

    if not t.deadline:
        errors.append(ValidationError("deadline", "required"))
    elif t.deadline.year < 2020:
        errors.append(ValidationError("deadline", f"suspiciously old: {t.deadline}"))

    if not t.country_code:
        errors.append(ValidationError("country_code", "required"))
    elif len(t.country_code) > 3:
        errors.append(ValidationError("country_code", "must be 2-3 char ISO code"))

    if not t.country_name:
        errors.append(ValidationError("country_name", "required"))

    if t.budget_usd is not None and t.budget_usd < 0:
        errors.append(ValidationError("budget_usd", "cannot be negative"))

    return errors


# ── Test runner ───────────────────────────────────────────────────────────────

@dataclass
class TestResult:
    source_id: str
    ok: bool
    fetched: int
    valid: int
    invalid: int
    errors: list[str]
    sample: list[TenderCreate]


async def test_crawler(crawler: BaseCrawler, limit: int = 5) -> TestResult:
    """
    Dry-run a crawler — fetch tenders and validate them without writing to DB.
    Use this during development to verify a new source works correctly.

    Example:
        from crawler.registry import get_crawler
        from crawler.plugin import test_crawler
        result = await test_crawler(get_crawler("sam_gov"))
    """
    errors: list[str] = []

    try:
        tenders = await crawler.fetch_tenders()
    except Exception as e:
        return TestResult(
            source_id=crawler.source_id,
            ok=False,
            fetched=0,
            valid=0,
            invalid=0,
            errors=[f"fetch_tenders() raised: {type(e).__name__}: {e}"],
            sample=[],
        )

    valid_count = 0
    invalid_count = 0
    external_ids_seen: set[str] = set()

    for t in tenders:
        # Check for duplicates within the batch
        if t.external_id in external_ids_seen:
            errors.append(f"Duplicate external_id in batch: {t.external_id!r}")
            invalid_count += 1
            continue
        external_ids_seen.add(t.external_id)

        validation_errors = validate_tender(t)
        if validation_errors:
            for ve in validation_errors:
                errors.append(f"[{t.external_id!r}] {ve.field}: {ve.message}")
            invalid_count += 1
        else:
            valid_count += 1

    return TestResult(
        source_id=crawler.source_id,
        ok=len(errors) == 0,
        fetched=len(tenders),
        valid=valid_count,
        invalid=invalid_count,
        errors=errors[:20],  # cap output
        sample=tenders[:limit],
    )
