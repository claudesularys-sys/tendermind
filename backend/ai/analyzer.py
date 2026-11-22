import json
from anthropic import AsyncAnthropic
from core.config import settings

_client: AsyncAnthropic | None = None


def get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


KEYWORDS = [
    "transformer", "трансформатор", "transformateur", "transformador", "trasformatore",
    "transformator", "تحويل", "变压器", "トランスフォーマー", "변압기",
    "kva", "kw", "mva", "power equipment", "электрооборудование",
    "substation", "подстанция", "switchgear", "силовой", "distribution transformer",
    "oil-cooled", "dry-type", "автотрансформатор", "voltage regulator",
    "power transformer", "силовой трансформатор", "transmission",
]


def keyword_prefilter(title: str, description: str | None) -> bool:
    text = f"{title} {description or ''}".lower()
    return any(kw in text for kw in KEYWORDS)


async def quick_check(
    tender_title: str,
    tender_description: str | None,
    equipment_hint: str | None,
    company_profile: dict,
) -> tuple[bool, str | None]:
    """
    Returns (is_match: bool, equipment_summary: str | None).
    Uses claude-haiku for speed and cost efficiency.
    """
    if not settings.anthropic_api_key:
        return True, None  # No AI key — pass everything through

    profile_text = _profile_to_text(company_profile)

    prompt = f"""You are a procurement matching assistant.

Company profile:
{profile_text}

Tender:
Title: {tender_title}
Description: {(tender_description or '')[:1000]}

Answer with JSON only, no other text:
{{
  "match": true or false,
  "equipment_summary": "one line describing exactly what equipment is needed (English, max 80 chars)" or null
}}

Match = true only if this tender likely requires transformers or power equipment matching the company profile.
If the tender is about construction, IT, consulting, food, uniforms, vehicles — match = false."""

    try:
        response = await get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        data = json.loads(text)
        return bool(data.get("match")), data.get("equipment_summary")
    except Exception as e:
        print(f"[AI] quick_check failed: {e}")
        # On AI failure, use keyword filter result as fallback
        return keyword_prefilter(tender_title, tender_description), None


def _profile_to_text(profile: dict) -> str:
    lines = []
    if profile.get("company_name"):
        lines.append(f"Company: {profile['company_name']}")
    if profile.get("transformer_types"):
        lines.append(f"Products: {', '.join(profile['transformer_types'])}")
    if profile.get("power_kva_min") or profile.get("power_kva_max"):
        lines.append(f"Power range: {profile.get('power_kva_min', 0)}-{profile.get('power_kva_max', 99999)} kVA")
    if profile.get("voltage_kv"):
        lines.append(f"Voltage: {', '.join(str(v) for v in profile['voltage_kv'])} kV")
    if profile.get("keywords_extra"):
        lines.append(f"Extra keywords: {', '.join(profile['keywords_extra'])}")
    return "\n".join(lines) if lines else "Power transformer manufacturer"
