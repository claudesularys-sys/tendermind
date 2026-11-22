"""
Zakupki.gov.ru — Russia State Procurement
Free public API (no auth needed for reading).
OKPD2 code for transformers: 27.11 (electric motors, generators, transformers)
"""
from datetime import date
from dateutil import parser as dateparser
from crawler.base import BaseCrawler, TenderCreate


class ZakupkiRuCrawler(BaseCrawler):
    source_id = "zakupki_ru"
    country_code = "RU"
    country_name = "Russia"
    region = "cis"
    base_url = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html"
    schedule = "0 */1 * * *"

    async def fetch_tenders(self) -> list[TenderCreate]:
        """
        Use the open data RSS/JSON feed — zakupki.gov.ru provides
        structured XML feeds for public procurements.
        """
        results = []
        async with self._client() as client:
            for keyword in ["трансформатор", "силовой трансформатор", "трансформаторная подстанция"]:
                try:
                    # Free JSON search endpoint (44-FZ, open data)
                    resp = await client.get(
                        "https://zakupki.gov.ru/epz/order/extendedsearch/rss.html",
                        params={
                            "searchString": keyword,
                            "morphology": "on",
                            "pageNumber": 1,
                            "sortDirection": "false",
                            "recordsPerPage": "_50",
                            "showLotsInfoHidden": "false",
                            "fz44": "on",
                            "fz223": "on",
                            "af": "on",
                        },
                    )
                    if resp.status_code == 200:
                        items = _parse_rss(resp.text, keyword)
                        results.extend(items)
                except Exception as e:
                    print(f"[zakupki_ru] Error for '{keyword}': {e}")
        return _deduplicate(results)


def _parse_rss(xml_text: str, source_keyword: str) -> list[TenderCreate]:
    """Parse RSS XML from zakupki.gov.ru."""
    import xml.etree.ElementTree as ET
    tenders = []
    try:
        root = ET.fromstring(xml_text)
        channel = root.find("channel")
        if channel is None:
            return []
        for item in channel.findall("item"):
            guid = (item.findtext("guid") or "").strip()
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = item.findtext("pubDate") or ""
            description = (item.findtext("description") or "").strip()

            if not (guid and title and link):
                continue

            # Parse deadline from description (rough extraction)
            deadline = _extract_deadline(description, pub_date)
            if not deadline or deadline < date.today():
                continue

            tenders.append(TenderCreate(
                external_id=f"ru_{guid}",
                source_id="zakupki_ru",
                country_code="RU",
                country_name="Russia",
                title=title[:500],
                description=description[:2000],
                deadline=deadline,
                url=link,
                raw_data={"guid": guid},
            ))
    except Exception as e:
        print(f"[zakupki_ru] RSS parse error: {e}")
    return tenders


def _extract_deadline(description: str, pub_date: str) -> date | None:
    """
    Try to extract the submission deadline from HTML description.
    Fallback: pub_date + 30 days (rough estimate).
    """
    import re
    from dateutil import parser as dp
    from datetime import timedelta

    # Look for date patterns like "31.12.2026" or "31/12/2026"
    matches = re.findall(r'(\d{2}[.\/]\d{2}[.\/]\d{4})', description)
    dates = []
    for m in matches:
        try:
            d = dp.parse(m, dayfirst=True).date()
            if d > date.today():
                dates.append(d)
        except Exception:
            pass
    if dates:
        return min(dates)

    # Fallback
    try:
        return dp.parse(pub_date).date() + timedelta(days=30)
    except Exception:
        return None


def _deduplicate(tenders: list[TenderCreate]) -> list[TenderCreate]:
    seen = set()
    result = []
    for t in tenders:
        if t.external_id not in seen:
            seen.add(t.external_id)
            result.append(t)
    return result
