"""
World Bank Procurement Notices
API: https://search.worldbank.org/api/v2/procurement
Free public API — no key needed.
"""
from datetime import date
from dateutil import parser as dateparser
from crawler.base import BaseCrawler, TenderCreate


class WorldBankCrawler(BaseCrawler):
    source_id = "world_bank"
    country_code = "WB"
    country_name = "World Bank"
    region = "international"
    base_url = "https://search.worldbank.org/api/v2/procurement"
    schedule = "0 */2 * * *"  # every 2 hours (slower-moving source)

    async def fetch_tenders(self) -> list[TenderCreate]:
        results = []
        async with self._client() as client:
            for query in ["transformer", "power equipment", "substation"]:
                try:
                    params = {
                        "format": "json",
                        "qterm": query,
                        "rows": 50,
                        "os": 0,
                    }
                    resp = await client.get(self.base_url, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    docs = data.get("procnotices", {})
                    if isinstance(docs, dict):
                        docs = list(docs.values())
                    for doc in docs:
                        tender = self._normalize(doc)
                        if tender:
                            results.append(tender)
                except Exception as e:
                    print(f"[world_bank] Error for '{query}': {e}")

        return _deduplicate(results)

    def _normalize(self, doc: dict) -> TenderCreate | None:
        notice_id = doc.get("id") or doc.get("noticelinkid")
        if not notice_id:
            return None

        title = doc.get("project_name") or doc.get("notice_no") or ""
        if not title:
            return None

        deadline_str = doc.get("deadline_dt") or doc.get("submission_date")
        if not deadline_str:
            return None
        try:
            deadline = dateparser.parse(str(deadline_str)).date()
        except Exception:
            return None

        if deadline < date.today():
            return None

        country_code = (doc.get("countryshortname") or "")[:2].upper() or "WB"
        country_name = doc.get("countryname") or "World Bank Project"

        url = (
            doc.get("url")
            or f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{notice_id}"
        )

        return TenderCreate(
            external_id=f"wb_{notice_id}",
            source_id=self.source_id,
            country_code=country_code,
            country_name=country_name,
            title=str(title)[:500],
            description=doc.get("notice_text", "")[:2000],
            deadline=deadline,
            url=url,
            raw_data={"id": notice_id, "project_id": doc.get("project_id")},
        )


def _deduplicate(tenders: list[TenderCreate]) -> list[TenderCreate]:
    seen = set()
    result = []
    for t in tenders:
        if t.external_id not in seen:
            seen.add(t.external_id)
            result.append(t)
    return result
