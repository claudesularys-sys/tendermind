"""
GeM — Government e-Marketplace (India)
API: https://mkp.gem.gov.in/api (public search)
India is one of the largest transformer markets globally.
"""
from datetime import date
from dateutil import parser as dateparser
from crawler.base import BaseCrawler, TenderCreate


class GemIndiaCrawler(BaseCrawler):
    source_id = "gem_india"
    country_code = "IN"
    country_name = "India"
    region = "asia"
    base_url = "https://bidplus.gem.gov.in/all-bids"
    schedule = "0 */1 * * *"  # hourly

    async def fetch_tenders(self) -> list[TenderCreate]:
        results = []
        async with self._client() as client:
            for keyword in ["transformer", "power transformer", "distribution transformer"]:
                try:
                    # GeM public API endpoint
                    resp = await client.get(
                        "https://mkp.gem.gov.in/api/public/bids/search",
                        params={
                            "searchText": keyword,
                            "pageNo": 1,
                            "pageSize": 50,
                            "sortBy": "bid_end_date",
                            "sortOrder": "asc",
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for bid in data.get("data", {}).get("bids", []):
                            t = self._normalize(bid)
                            if t:
                                results.append(t)
                except Exception as e:
                    print(f"[gem_india] Error for '{keyword}': {e}")
        return _deduplicate(results)

    def _normalize(self, bid: dict) -> TenderCreate | None:
        bid_id = bid.get("bid_number") or bid.get("id")
        if not bid_id:
            return None

        title = bid.get("item_name") or bid.get("title", "")
        deadline_str = bid.get("bid_end_date") or bid.get("end_date")
        if not deadline_str:
            return None

        try:
            deadline = dateparser.parse(str(deadline_str)).date()
        except Exception:
            return None

        if deadline < date.today():
            return None

        city = bid.get("consignee_location") or bid.get("location")
        quantity = bid.get("total_quantity", "")
        amount = bid.get("bid_amount")
        usd_amount = float(amount) / 84 if amount else None  # INR → USD approx

        return TenderCreate(
            external_id=f"gem_in_{bid_id}",
            source_id=self.source_id,
            country_code=self.country_code,
            country_name=self.country_name,
            city=city,
            title=f"{title} (Qty: {quantity})" if quantity else title,
            title_en=title[:500],
            deadline=deadline,
            url=f"https://bidplus.gem.gov.in/bidlists/{bid_id}",
            budget_usd=usd_amount,
            currency_original="INR",
            budget_original=float(amount) if amount else None,
            raw_data={"bid_id": bid_id},
        )


def _deduplicate(tenders: list[TenderCreate]) -> list[TenderCreate]:
    seen = set()
    result = []
    for t in tenders:
        if t.external_id not in seen:
            seen.add(t.external_id)
            result.append(t)
    return result
