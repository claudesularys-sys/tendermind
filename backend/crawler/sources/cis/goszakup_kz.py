"""
GosZakup — Kazakhstan State Procurement
GraphQL API: https://goszakup.gov.kz/v3/graphql
Requires Bearer token — register at https://goszakup.gov.kz
"""
import os
from datetime import date
from dateutil import parser as dateparser
from crawler.base import BaseCrawler, TenderCreate

GRAPHQL_URL = "https://goszakup.gov.kz/v3/graphql"
GOSZAKUP_TOKEN = os.getenv("GOSZAKUP_TOKEN", "")

QUERY = """
query SearchTenders($keywords: String!, $limit: Int!) {
  allTrdBuy(
    filter: { nameRu: { contains: $keywords }, statusId: { equalTo: 2 } }
    first: $limit
    orderBy: END_DATE_DESC
  ) {
    nodes {
      id
      numberAnno
      nameRu
      totalSumm
      startDate
      endDate
      orgBin
      lots {
        nodes {
          nameRu
          amount
        }
      }
    }
  }
}
"""


class GoszakupKzCrawler(BaseCrawler):
    source_id = "goszakup_kz"
    country_code = "KZ"
    country_name = "Kazakhstan"
    region = "cis"
    base_url = GRAPHQL_URL
    schedule = "*/30 * * * *"

    async def fetch_tenders(self) -> list[TenderCreate]:
        if not GOSZAKUP_TOKEN:
            print("[goszakup_kz] No token configured — using keyword search fallback")
            return await self._fetch_web_fallback()

        results = []
        async with self._client(headers={"Authorization": f"Bearer {GOSZAKUP_TOKEN}"}) as client:
            for keyword in ["трансформатор", "силовой трансформатор", "трансформаторная"]:
                try:
                    resp = await client.post(
                        self.base_url,
                        json={"query": QUERY, "variables": {"keywords": keyword, "limit": 50}},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    nodes = data.get("data", {}).get("allTrdBuy", {}).get("nodes", [])
                    for node in nodes:
                        tender = self._normalize(node)
                        if tender:
                            results.append(tender)
                except Exception as e:
                    print(f"[goszakup_kz] Error for '{keyword}': {e}")

        return _deduplicate(results)

    def _normalize(self, node: dict) -> TenderCreate | None:
        node_id = node.get("id") or node.get("numberAnno")
        if not node_id:
            return None

        deadline_str = node.get("endDate")
        if not deadline_str:
            return None
        try:
            deadline = dateparser.parse(str(deadline_str)).date()
        except Exception:
            return None

        if deadline < date.today():
            return None

        title = node.get("nameRu", "")
        budget = node.get("totalSumm")
        try:
            budget_float = float(budget) if budget else None
            budget_usd = budget_float / 470 if budget_float else None  # approximate KZT→USD
        except Exception:
            budget_usd = None

        return TenderCreate(
            external_id=f"goszakup_{node_id}",
            source_id=self.source_id,
            country_code=self.country_code,
            country_name=self.country_name,
            title=title[:500],
            description=None,
            deadline=deadline,
            url=f"https://goszakup.gov.kz/ru/announce/index/{node_id}",
            budget_usd=budget_usd,
            currency_original="KZT",
            budget_original=budget_float,
            raw_data={"id": node_id, "org_bin": node.get("orgBin")},
        )

    async def _fetch_web_fallback(self) -> list[TenderCreate]:
        """
        Fallback when no API token: scrape public search page then
        fetch individual announce pages in parallel to get deadlines.
        """
        import re
        import asyncio

        results = []
        headers = {"User-Agent": "Mozilla/5.0 (compatible; TenderMind/1.0)"}

        async with self._client() as client:
            for keyword in ["трансформатор", "силовой трансформатор"]:
                try:
                    resp = await client.get(
                        "https://goszakup.gov.kz/ru/search/lots",
                        params={"filter[name]": keyword, "filter[trade_status]": "2"},
                        headers=headers,
                    )
                    if resp.status_code != 200:
                        print(f"[goszakup_kz] Search page {resp.status_code} for '{keyword}'")
                        continue

                    html = resp.text
                    rows = re.findall(
                        r'/ru/announce/index/(\d+)[^"]*"[^>]*>(.*?)</tr>',
                        html, re.DOTALL,
                    )

                    seen: set[str] = set()
                    announce_data: dict[str, dict] = {}
                    for announce_id, row_html in rows:
                        if announce_id in seen:
                            continue
                        seen.add(announce_id)

                        text = re.sub(r'<[^>]+>', ' ', row_html)
                        text = re.sub(r'\s+', ' ', text).strip()

                        # Title: text before "Заказчик:"
                        title_m = re.match(r'[\d-]+\s+(.+?)(?:\s+Заказчик:|$)', text)
                        title = title_m.group(1).strip() if title_m else text[:120]

                        # Amount (e.g. "1 700 000.00")
                        amount_m = re.search(r'([\d\s]{3,}[.,]\d{2})', text)
                        amount: float | None = None
                        if amount_m:
                            try:
                                amount = float(
                                    amount_m.group(1).replace(' ', '').replace(',', '.')
                                )
                            except ValueError:
                                pass

                        announce_data[announce_id] = {"title": title, "amount": amount}

                    print(
                        f"[goszakup_kz] Found {len(announce_data)} announces for '{keyword}'"
                    )

                    # Fetch detail pages in parallel (cap at 20) to get deadlines
                    async def _get_deadline(aid: str) -> tuple[str, str | None]:
                        try:
                            r = await client.get(
                                f"https://goszakup.gov.kz/ru/announce/index/{aid}",
                                headers=headers,
                            )
                            m = re.search(
                                r'окончания приема заявок.*?value="([^"]+)"',
                                r.text, re.DOTALL | re.IGNORECASE,
                            )
                            return aid, m.group(1) if m else None
                        except Exception:
                            return aid, None

                    deadline_results = await asyncio.gather(
                        *[_get_deadline(aid) for aid in list(announce_data.keys())[:20]]
                    )

                    for aid, deadline_str in deadline_results:
                        if not deadline_str:
                            continue
                        try:
                            deadline = dateparser.parse(deadline_str).date()
                        except Exception:
                            continue
                        if deadline < date.today():
                            continue

                        info = announce_data[aid]
                        budget_kzt = info["amount"]
                        results.append(TenderCreate(
                            external_id=f"goszakup_{aid}",
                            source_id=self.source_id,
                            country_code=self.country_code,
                            country_name=self.country_name,
                            title=info["title"][:500],
                            deadline=deadline,
                            url=f"https://goszakup.gov.kz/ru/announce/index/{aid}",
                            budget_original=budget_kzt,
                            currency_original="KZT",
                            budget_usd=budget_kzt / 470 if budget_kzt else None,
                            raw_data={"id": aid},
                        ))

                except Exception as e:
                    print(f"[goszakup_kz] Fallback error for '{keyword}': {e}")

        return results


def _deduplicate(tenders: list[TenderCreate]) -> list[TenderCreate]:
    seen = set()
    result = []
    for t in tenders:
        if t.external_id not in seen:
            seen.add(t.external_id)
            result.append(t)
    return result
