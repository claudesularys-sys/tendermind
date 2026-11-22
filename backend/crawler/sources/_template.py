"""
TenderMind Source Plugin — Template
=====================================

HOW TO ADD A NEW SOURCE IN 10-15 MINUTES
-----------------------------------------

Step 1: Copy this file to the correct region folder:
  backend/crawler/sources/<region>/<source_id>.py

  Regions: americas | europe | asia | cis | mena | international

Step 2: Fill in the class attributes and implement fetch_tenders()

Step 3: Test without touching the DB:
  python -m crawler.cli test TEMPLATE_SOURCE_ID

Step 4: Run and save to DB:
  python -m crawler.cli run TEMPLATE_SOURCE_ID

Step 5: Done! The system auto-discovers the file on next restart.

NOTES:
  ✓ Only implement fetch_tenders() and optionally _normalize()
  ✓ Do NOT call DB, send alerts, or run AI — the pipeline handles that
  ✓ For broken/unavailable sources, catch exceptions and return []
  ✓ The keyword pre-filter runs AFTER your code, not inside it
"""
from datetime import date
from dateutil import parser as dateparser
from crawler.base import BaseCrawler, TenderCreate


class TemplateCrawler(BaseCrawler):
    # ── Required: fill these in ──────────────────────────────────────────────
    source_id    = "TEMPLATE_SOURCE_ID"    # unique, snake_case: "austender_au"
    country_code = "TEMPLATE_COUNTRY_CODE" # ISO 3166-1 alpha-2: "AU"
    country_name = "TEMPLATE_COUNTRY_NAME" # display: "Australia"
    region       = "TEMPLATE_REGION"       # americas|europe|asia|cis|mena|international
    base_url     = "https://"              # source API or homepage

    # ── Optional: override default 30-min schedule ──────────────────────────
    # schedule = "0 */2 * * *"   # every 2 hours — for slower sources

    async def fetch_tenders(self) -> list[TenderCreate]:
        """
        Fetch tenders from the source. Must return list[TenderCreate].

        TenderCreate fields
        -------------------
        REQUIRED:
          external_id   str   "<source_id>_<raw_id>"  e.g. "austender_123"
          source_id     str   use: self.source_id
          country_code  str   use: self.country_code
          country_name  str   use: self.country_name
          title         str   max 500 chars
          deadline      date  date object — skip if deadline < date.today()
          url           str   direct link to the official notice

        OPTIONAL (add when available):
          city          str
          title_en      str   English translation for non-English sources
          description   str   max 2000 chars
          budget_usd    float estimate in USD (convert if needed)
          currency_original  str  e.g. "EUR", "GBP", "KZT"
          budget_original    float value in original currency
        """
        results = []

        async with self._client() as client:
            # ── OPTION A: REST JSON API ──────────────────────────────────
            # for keyword in ["transformer", "power equipment"]:
            #     try:
            #         resp = await client.get(
            #             self.base_url + "/api/tenders",
            #             params={"q": keyword, "status": "open", "limit": 100},
            #         )
            #         resp.raise_for_status()
            #         for item in resp.json().get("results", []):
            #             t = self._normalize(item)
            #             if t:
            #                 results.append(t)
            #     except Exception as e:
            #         print(f"[{self.source_id}] Error: {e}")

            # ── OPTION B: GraphQL API ────────────────────────────────────
            # QUERY = "query { tenders(filter: { title: { contains: $kw }}) { ... } }"
            # resp = await client.post(self.base_url, json={"query": QUERY, ...})

            # ── OPTION C: XML / RSS feed ─────────────────────────────────
            # import xml.etree.ElementTree as ET
            # resp = await client.get(self.base_url + "/feed.rss")
            # root = ET.fromstring(resp.text)
            # for item in root.findall(".//item"): ...

            # ── OPTION D: HTML scraping (last resort) ────────────────────
            # Use only when no API/feed is available
            # from playwright.async_api import async_playwright
            # async with async_playwright() as p:
            #     browser = await p.chromium.launch()
            #     page = await browser.new_page()
            #     await page.goto(self.base_url)
            #     ...

            pass  # TODO: replace with your implementation

        return _deduplicate(results)

    def _normalize(self, item: dict) -> TenderCreate | None:
        """Convert one raw API item into TenderCreate. Return None to skip."""

        # 1. Extract unique ID
        item_id = item.get("id") or item.get("noticeId") or item.get("number")
        if not item_id:
            return None

        # 2. Extract title
        title = (item.get("title") or item.get("name") or item.get("subject") or "").strip()
        if not title:
            return None

        # 3. Parse deadline — must be a Python date object
        deadline_raw = (
            item.get("deadline") or item.get("closingDate") or
            item.get("submission_date") or item.get("end_date")
        )
        if not deadline_raw:
            return None
        try:
            deadline = dateparser.parse(str(deadline_raw)).date()
        except Exception:
            return None

        # 4. Skip expired
        if deadline < date.today():
            return None

        # 5. Build official URL
        url = item.get("url") or item.get("link") or f"{self.base_url}/notice/{item_id}"

        # 6. Optional: city, budget
        city = item.get("city") or item.get("location") or item.get("place")
        budget_raw = item.get("value") or item.get("amount") or item.get("budget")
        budget_usd = None
        if budget_raw:
            try:
                budget_usd = float(budget_raw)
                # Convert if needed, e.g.: budget_usd = float(budget_raw) / 1.08  # EUR→USD
            except (ValueError, TypeError):
                pass

        return TenderCreate(
            external_id=f"{self.source_id}_{item_id}",
            source_id=self.source_id,
            country_code=self.country_code,
            country_name=self.country_name,
            city=city,
            title=title[:500],
            deadline=deadline,
            url=url,
            budget_usd=budget_usd,
            raw_data={"id": item_id},  # keep for debugging
        )


def _deduplicate(tenders: list[TenderCreate]) -> list[TenderCreate]:
    """Remove duplicates within the current batch by external_id."""
    seen: set[str] = set()
    result = []
    for t in tenders:
        if t.external_id not in seen:
            seen.add(t.external_id)
            result.append(t)
    return result
