"""
UNGM — United Nations Global Marketplace
URL: https://www.ungm.org/Public/Notice
Scraped via public search (no API key needed).
"""
from datetime import date
from dateutil import parser as dateparser
from crawler.base import BaseCrawler, TenderCreate


class UNGMCrawler(BaseCrawler):
    source_id = "ungm"
    country_code = "UN"
    country_name = "United Nations"
    region = "international"
    base_url = "https://www.ungm.org/Public/Notice"
    schedule = "0 */2 * * *"

    async def fetch_tenders(self) -> list[TenderCreate]:
        results = []
        async with self._client() as client:
            for keyword in ["transformer", "power equipment", "electrical equipment"]:
                try:
                    resp = await client.get(
                        "https://www.ungm.org/Public/Notice/SearchApi",
                        params={
                            "description": keyword,
                            "pageIndex": 1,
                            "pageSize": 50,
                        },
                        headers={"Accept": "application/json"},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    for notice in data.get("notices", data if isinstance(data, list) else []):
                        t = self._normalize(notice)
                        if t:
                            results.append(t)
                except Exception as e:
                    print(f"[ungm] Error for '{keyword}': {e}")
        return _deduplicate(results)

    def _normalize(self, notice: dict) -> TenderCreate | None:
        notice_id = notice.get("NoticeId") or notice.get("id")
        if not notice_id:
            return None

        title = notice.get("Title") or notice.get("title", "")
        deadline_str = notice.get("Deadline") or notice.get("deadline")
        if not deadline_str:
            return None

        try:
            deadline = dateparser.parse(str(deadline_str)).date()
        except Exception:
            return None

        if deadline < date.today():
            return None

        org = notice.get("AgencyName") or "UN Agency"

        return TenderCreate(
            external_id=f"ungm_{notice_id}",
            source_id=self.source_id,
            country_code=self.country_code,
            country_name=org,
            title=title[:500],
            title_en=title[:500],
            deadline=deadline,
            url=f"https://www.ungm.org/Public/Notice/{notice_id}",
            raw_data={"id": notice_id, "agency": org},
        )


def _deduplicate(tenders: list[TenderCreate]) -> list[TenderCreate]:
    seen = set()
    result = []
    for t in tenders:
        if t.external_id not in seen:
            seen.add(t.external_id)
            result.append(t)
    return result
