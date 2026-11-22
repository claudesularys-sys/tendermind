import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional
import httpx


@dataclass
class TenderCreate:
    # ── Required ──────────────────────────────────────────────────────────────
    external_id: str        # unique: "<source_id>_<raw_id>", e.g. "sam_gov_ABC123"
    source_id: str          # matches BaseCrawler.source_id
    country_code: str       # ISO 3166-1 alpha-2, or EU / UN / WB
    country_name: str       # display name
    title: str              # max 500 chars
    deadline: date          # submission deadline — future date only
    url: str                # official link to the tender notice

    # ── Optional ──────────────────────────────────────────────────────────────
    city: Optional[str] = None
    title_en: Optional[str] = None        # English translation when source is non-English
    equipment_summary: Optional[str] = None  # filled in by Claude after matching
    description: Optional[str] = None    # max 2000 chars
    budget_usd: Optional[float] = None   # converted to USD
    currency_original: Optional[str] = None
    budget_original: Optional[float] = None
    raw_data: Optional[dict] = None      # original API response for debugging


@dataclass
class CrawlResult:
    source_id: str
    fetched: int = 0
    new_tenders: int = 0
    matched: int = 0
    status: str = "ok"
    error_msg: Optional[str] = None
    duration_ms: Optional[int] = None


class BaseCrawler(ABC):
    source_id: str = ""
    country_code: str = ""
    country_name: str = ""
    region: str = ""        # americas | europe | asia | cis | mena | international
    base_url: str = ""
    schedule: str = "*/30 * * * *"  # cron — default: every 30 min

    def _client(self, **kwargs) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "TenderMind/1.0 (+https://tendermind.ai)"},
            follow_redirects=True,
            **kwargs,
        )

    @abstractmethod
    async def fetch_tenders(self) -> list[TenderCreate]:
        """
        Fetch tenders from this source and return normalized TenderCreate objects.
        - Do NOT filter by deadline here — the pipeline handles that.
        - Do NOT deduplicate by DB — only deduplicate within the current batch.
        - Do NOT save to DB — return the list and let the pipeline handle persistence.
        - Catch all exceptions internally; log and return partial results.
        """

    async def run(self) -> tuple[CrawlResult, list[TenderCreate]]:
        """
        Entry point called by the scheduler.
        Returns (CrawlResult stats, list of fetched tenders).
        Callers must use the returned tenders — do not call fetch_tenders() again.
        """
        start = time.time()
        result = CrawlResult(source_id=self.source_id)
        tenders: list[TenderCreate] = []
        try:
            tenders = await self.fetch_tenders()
            result.fetched = len(tenders)
            result.status = "ok"
        except Exception as e:
            result.status = "error"
            result.error_msg = str(e)[:500]
            print(f"[{self.source_id}] Crawler error: {e}")
        result.duration_ms = int((time.time() - start) * 1000)
        return result, tenders
