"""
Find a Tender (UK) — UK Government tender portal (post-Brexit)
API: https://www.find-tender.service.gov.uk/api/1.0/ocds/
Free public API, no auth required.
"""
from datetime import date
from dateutil import parser as dateparser
from crawler.base import BaseCrawler, TenderCreate


class FindATenderUKCrawler(BaseCrawler):
    source_id = "find_a_tender_uk"
    country_code = "GB"
    country_name = "United Kingdom"
    region = "europe"
    base_url = "https://www.find-tender.service.gov.uk/api/1.0/ocds/opportunities"
    schedule = "*/30 * * * *"

    async def fetch_tenders(self) -> list[TenderCreate]:
        results = []
        async with self._client() as client:
            for keyword in ["transformer", "substation", "power equipment", "switchgear"]:
                try:
                    params = {
                        "q": keyword,
                        "limit": 100,
                        "offset": 0,
                    }
                    resp = await client.get(self.base_url, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    for release in data.get("releases", []):
                        tender = self._normalize(release)
                        if tender:
                            results.append(tender)
                except Exception as e:
                    print(f"[find_a_tender_uk] Error for '{keyword}': {e}")
        return _deduplicate(results)

    def _normalize(self, release: dict) -> TenderCreate | None:
        ocid = release.get("ocid", "")
        if not ocid:
            return None

        tender = release.get("tender", {})
        title = tender.get("title", "")
        if not title:
            return None

        # Deadline: look in tender.tenderPeriod.endDate
        period = tender.get("tenderPeriod", {})
        deadline_str = period.get("endDate")
        if not deadline_str:
            return None
        try:
            deadline = dateparser.parse(deadline_str).date()
        except Exception:
            return None

        if deadline < date.today():
            return None

        # Location
        buyer = release.get("buyer", {})
        address = buyer.get("address", {})
        city = address.get("locality") or address.get("region")

        # Value
        value_obj = tender.get("value", {})
        amount = value_obj.get("amount")
        currency = value_obj.get("currency", "GBP")
        usd_amount = float(amount) * 1.27 if amount else None  # approx GBP→USD

        url = f"https://www.find-tender.service.gov.uk/Notice/{ocid.split('-')[-1]}"

        return TenderCreate(
            external_id=f"uk_fat_{ocid}",
            source_id=self.source_id,
            country_code=self.country_code,
            country_name=self.country_name,
            city=city,
            title=title[:500],
            title_en=title[:500],
            description=tender.get("description", "")[:2000],
            deadline=deadline,
            url=url,
            budget_usd=usd_amount,
            currency_original=currency,
            budget_original=float(amount) if amount else None,
            raw_data={"ocid": ocid},
        )


def _deduplicate(tenders: list[TenderCreate]) -> list[TenderCreate]:
    seen = set()
    result = []
    for t in tenders:
        if t.external_id not in seen:
            seen.add(t.external_id)
            result.append(t)
    return result
