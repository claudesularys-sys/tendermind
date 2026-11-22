"""
SAM.gov (USA) — System for Award Management
API: https://api.sam.gov/opportunities/v2/search
Free API key: https://sam.gov/content/entity-registration
"""
from datetime import date, datetime
from dateutil import parser as dateparser
from crawler.base import BaseCrawler, TenderCreate
from core.config import settings

TRANSFORMER_KEYWORDS = [
    "transformer", "power transformer", "distribution transformer",
    "substation", "switchgear", "high voltage", "kVA", "MVA",
]


class SamGovCrawler(BaseCrawler):
    source_id = "sam_gov"
    country_code = "US"
    country_name = "United States"
    region = "americas"
    base_url = "https://api.sam.gov/opportunities/v2/search"
    schedule = "*/30 * * * *"

    async def fetch_tenders(self) -> list[TenderCreate]:
        if not settings.sam_gov_api_key:
            print("[sam_gov] No API key configured — skipping")
            return []

        results = []
        async with self._client() as client:
            for keyword in ["power transformer", "distribution transformer", "substation equipment"]:
                params = {
                    "api_key": settings.sam_gov_api_key,
                    "keywords": keyword,
                    "limit": 100,
                    "offset": 0,
                    "postedFrom": _six_months_ago(),
                    "active": "Yes",
                }
                try:
                    resp = await client.get(self.base_url, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    for opp in data.get("opportunitiesData", []):
                        tender = self._normalize(opp)
                        if tender:
                            results.append(tender)
                except Exception as e:
                    print(f"[sam_gov] Error fetching keyword '{keyword}': {e}")

        return _deduplicate(results)

    def _normalize(self, opp: dict) -> TenderCreate | None:
        notice_id = opp.get("noticeId") or opp.get("solicitationNumber")
        if not notice_id:
            return None

        title = opp.get("title", "")
        deadline_str = opp.get("responseDeadLine") or opp.get("archiveDate")
        if not deadline_str:
            return None

        try:
            deadline = dateparser.parse(deadline_str).date()
        except Exception:
            return None

        if deadline < date.today():
            return None

        place = opp.get("placeOfPerformance", {})
        city = place.get("city", {}).get("name") if isinstance(place, dict) else None
        state = place.get("state", {}).get("code") if isinstance(place, dict) else None
        city_full = f"{city}, {state}" if city and state else city

        org = opp.get("organizationType", "")
        url = f"https://sam.gov/opp/{opp.get('noticeId', '')}/view"

        return TenderCreate(
            external_id=f"samgov_{notice_id}",
            source_id=self.source_id,
            country_code=self.country_code,
            country_name=self.country_name,
            city=city_full,
            title=title,
            title_en=title,
            description=opp.get("description", "")[:2000],
            deadline=deadline,
            url=url,
            raw_data={"notice_id": notice_id, "type": opp.get("type")},
        )


def _six_months_ago() -> str:
    from dateutil.relativedelta import relativedelta
    d = date.today() - relativedelta(months=6)
    return d.strftime("%m/%d/%Y")


def _deduplicate(tenders: list[TenderCreate]) -> list[TenderCreate]:
    seen = set()
    result = []
    for t in tenders:
        if t.external_id not in seen:
            seen.add(t.external_id)
            result.append(t)
    return result
