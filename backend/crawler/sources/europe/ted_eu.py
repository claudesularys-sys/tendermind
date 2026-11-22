"""
TED EU — Tenders Electronic Daily (covers all 27 EU countries + EEA)
API: https://api.ted.europa.eu/v3/notices/search
CPV codes for transformers: 31170000 (transformers), 31130000 (substation equipment)
Free public API — no key required.
"""
from datetime import date
from dateutil import parser as dateparser
from crawler.base import BaseCrawler, TenderCreate

CPV_TRANSFORMERS = ["31170000", "31130000", "31100000"]

COUNTRY_NAMES = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "CY": "Cyprus",
    "CZ": "Czech Republic", "DE": "Germany", "DK": "Denmark", "EE": "Estonia",
    "ES": "Spain", "FI": "Finland", "FR": "France", "GR": "Greece",
    "HR": "Croatia", "HU": "Hungary", "IE": "Ireland", "IT": "Italy",
    "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "MT": "Malta",
    "NL": "Netherlands", "PL": "Poland", "PT": "Portugal", "RO": "Romania",
    "SE": "Sweden", "SI": "Slovenia", "SK": "Slovakia",
    "NO": "Norway", "IS": "Iceland", "LI": "Liechtenstein",
}


class TedEuCrawler(BaseCrawler):
    source_id = "ted_eu"
    country_code = "EU"
    country_name = "European Union"
    region = "europe"
    base_url = "https://api.ted.europa.eu/v3/notices/search"
    schedule = "*/30 * * * *"

    async def fetch_tenders(self) -> list[TenderCreate]:
        results = []
        async with self._client() as client:
            # Search by CPV codes
            for cpv in CPV_TRANSFORMERS:
                try:
                    payload = {
                        "query": f"cpv=={cpv}",
                        "fields": [
                            "ND", "TI", "PC", "DT", "DD", "MA", "CY",
                            "TW", "AU", "OJ", "DS", "XM",
                        ],
                        "scope": 3,
                        "limit": 100,
                        "sortField": "DS",
                        "sortOrder": "desc",
                    }
                    resp = await client.post(self.base_url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    for notice in data.get("notices", []):
                        tender = self._normalize(notice)
                        if tender:
                            results.append(tender)
                except Exception as e:
                    print(f"[ted_eu] Error for CPV {cpv}: {e}")

            # Also search by keyword
            try:
                payload = {
                    "query": 'TI ~ "transformer" OR TI ~ "transformateur" OR TI ~ "Transformator"',
                    "fields": ["ND", "TI", "PC", "DT", "DD", "MA", "CY", "TW"],
                    "scope": 3,
                    "limit": 100,
                    "sortField": "DS",
                    "sortOrder": "desc",
                }
                resp = await client.post(self.base_url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                for notice in data.get("notices", []):
                    tender = self._normalize(notice)
                    if tender:
                        results.append(tender)
            except Exception as e:
                print(f"[ted_eu] Keyword search error: {e}")

        return _deduplicate(results)

    def _normalize(self, notice: dict) -> TenderCreate | None:
        nd = notice.get("ND")  # notice document number
        if not nd:
            return None

        title_obj = notice.get("TI", {})
        title = (
            title_obj.get("EN")
            or next(iter(title_obj.values()), "")
            if isinstance(title_obj, dict)
            else str(title_obj)
        )
        if not title:
            return None

        deadline_str = notice.get("DT") or notice.get("DD")
        if not deadline_str:
            return None
        try:
            deadline = dateparser.parse(str(deadline_str)).date()
        except Exception:
            return None

        if deadline < date.today():
            return None

        country_code = notice.get("CY", "EU")
        country_name = COUNTRY_NAMES.get(country_code, country_code)
        city = notice.get("TW")
        if isinstance(city, dict):
            city = city.get("EN") or next(iter(city.values()), None)

        url = f"https://ted.europa.eu/udl?uri=TED:NOTICE:{nd}:TEXT:EN:HTML"

        return TenderCreate(
            external_id=f"ted_{nd}",
            source_id=self.source_id,
            country_code=country_code,
            country_name=country_name,
            city=str(city) if city else None,
            title=str(title)[:500],
            title_en=str(title)[:500] if isinstance(title_obj, dict) and "EN" in title_obj else None,
            deadline=deadline,
            url=url,
            raw_data={"nd": nd, "cpv": notice.get("PC")},
        )


def _deduplicate(tenders: list[TenderCreate]) -> list[TenderCreate]:
    seen = set()
    result = []
    for t in tenders:
        if t.external_id not in seen:
            seen.add(t.external_id)
            result.append(t)
    return result
