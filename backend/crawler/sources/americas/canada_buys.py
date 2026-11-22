"""
CanadaBuys — Government of Canada procurement portal
API: https://canadabuys.canada.ca (GETS open data)
Free public access, no API key required.
Canada is a top-5 global buyer of power transformers.
"""
from datetime import date
from dateutil import parser as dateparser
from crawler.base import BaseCrawler, TenderCreate

# UNSPSC codes for transformers: 26110000 (power conditioning), 26111700 (transformers)
SEARCH_KEYWORDS = ["transformer", "power transformer", "distribution transformer", "substation"]


class CanadaBuysCrawler(BaseCrawler):
    source_id    = "canada_buys"
    country_code = "CA"
    country_name = "Canada"
    region       = "americas"
    base_url     = "https://canadabuys.canada.ca"
    schedule     = "*/30 * * * *"

    async def fetch_tenders(self) -> list[TenderCreate]:
        results = []
        async with self._client() as client:
            for keyword in SEARCH_KEYWORDS:
                try:
                    # CanadaBuys Open Data API (GETS)
                    resp = await client.get(
                        "https://canadabuys.canada.ca/en/get-procurement-data/tender-opportunities",
                        params={
                            "key": keyword,
                            "status": "open",
                            "format": "json",
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        items = data if isinstance(data, list) else data.get("hits", data.get("data", []))
                        for item in items:
                            t = self._normalize(item)
                            if t:
                                results.append(t)
                except Exception as e:
                    print(f"[canada_buys] Error for '{keyword}': {e}")

            # Also try BUYANDSELL legacy API (still active)
            if not results:
                results = await self._fetch_buyandsell(client)

        return _deduplicate(results)

    async def _fetch_buyandsell(self, client) -> list[TenderCreate]:
        """Fallback: BuyandSell.gc.ca open data RSS."""
        import xml.etree.ElementTree as ET
        results = []
        for keyword in ["transformer"]:
            try:
                resp = await client.get(
                    "https://buyandsell.gc.ca/cds/public/2020/tender/search",
                    params={
                        "f": "json",
                        "searchTerms": keyword,
                        "status": "active",
                        "numberOfResults": "100",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("items", []):
                        t = self._normalize_buyandsell(item)
                        if t:
                            results.append(t)
            except Exception as e:
                print(f"[canada_buys] BuyandSell fallback error: {e}")
        return results

    def _normalize(self, item: dict) -> TenderCreate | None:
        notice_id = (
            item.get("id") or item.get("noticeId") or
            item.get("solicitationNumber") or item.get("reference_number")
        )
        if not notice_id:
            return None

        title = (
            item.get("title") or item.get("name") or
            item.get("genericTitle", {}).get("en", "") if isinstance(item.get("genericTitle"), dict) else ""
        )
        if not title:
            return None

        deadline_raw = (
            item.get("closingDate") or item.get("deadline") or
            item.get("tenderClosingDate") or item.get("bidClosingDate")
        )
        if not deadline_raw:
            return None
        try:
            deadline = dateparser.parse(str(deadline_raw)).date()
        except Exception:
            return None

        if deadline < date.today():
            return None

        org = item.get("department") or item.get("buyerName") or "Government of Canada"
        province = item.get("deliveryRegion") or item.get("region") or item.get("province")

        notice_type = item.get("noticeType") or ""
        slug = str(notice_id).replace(" ", "-")
        url = (
            item.get("url") or
            f"https://canadabuys.canada.ca/en/tender-opportunities/notice/{slug}"
        )

        return TenderCreate(
            external_id=f"canada_{notice_id}",
            source_id=self.source_id,
            country_code=self.country_code,
            country_name=self.country_name,
            city=province,
            title=str(title)[:500],
            title_en=str(title)[:500],
            description=item.get("description", "")[:2000],
            deadline=deadline,
            url=url,
            raw_data={"id": notice_id, "org": org, "type": notice_type},
        )

    def _normalize_buyandsell(self, item: dict) -> TenderCreate | None:
        notice_id = item.get("referenceNumber") or item.get("id")
        if not notice_id:
            return None
        title = item.get("title", {}).get("en") or item.get("title") or ""
        if not title:
            return None
        deadline_raw = item.get("closingDate") or item.get("tenderClosingDate")
        if not deadline_raw:
            return None
        try:
            deadline = dateparser.parse(str(deadline_raw)).date()
        except Exception:
            return None
        if deadline < date.today():
            return None

        return TenderCreate(
            external_id=f"canada_{notice_id}",
            source_id=self.source_id,
            country_code=self.country_code,
            country_name=self.country_name,
            title=str(title)[:500],
            title_en=str(title)[:500],
            deadline=deadline,
            url=f"https://buyandsell.gc.ca/procurement-data/tender-notice/{notice_id}",
            raw_data={"id": notice_id},
        )


def _deduplicate(tenders: list[TenderCreate]) -> list[TenderCreate]:
    seen: set[str] = set()
    result = []
    for t in tenders:
        if t.external_id not in seen:
            seen.add(t.external_id)
            result.append(t)
    return result
