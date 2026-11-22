"""
Telegram alert sender — called from the matching pipeline.
Sends a formatted message for each matched tender.
"""
from datetime import date
import httpx
from core.config import settings
from crawler.base import TenderCreate

FLAG_MAP = {
    "US": "🇺🇸", "GB": "🇬🇧", "DE": "🇩🇪", "FR": "🇫🇷", "IT": "🇮🇹",
    "ES": "🇪🇸", "PL": "🇵🇱", "NL": "🇳🇱", "BE": "🇧🇪", "SE": "🇸🇪",
    "NO": "🇳🇴", "FI": "🇫🇮", "DK": "🇩🇰", "AT": "🇦🇹", "CH": "🇨🇭",
    "CA": "🇨🇦", "AU": "🇦🇺", "NZ": "🇳🇿", "JP": "🇯🇵", "KR": "🇰🇷",
    "CN": "🇨🇳", "IN": "🇮🇳", "SG": "🇸🇬", "MY": "🇲🇾", "TH": "🇹🇭",
    "KZ": "🇰🇿", "RU": "🇷🇺", "UA": "🇺🇦", "BY": "🇧🇾", "UZ": "🇺🇿",
    "KG": "🇰🇬", "AZ": "🇦🇿", "TR": "🇹🇷", "SA": "🇸🇦", "AE": "🇦🇪",
    "QA": "🇶🇦", "KW": "🇰🇼", "EG": "🇪🇬", "NG": "🇳🇬", "ZA": "🇿🇦",
    "KE": "🇰🇪", "BR": "🇧🇷", "MX": "🇲🇽", "CL": "🇨🇱", "AR": "🇦🇷",
    "EU": "🇪🇺", "UN": "🇺🇳", "WB": "🌍",
}


async def send_tender_alert(chat_id: int, tender: TenderCreate, equipment_summary: str | None = None):
    if not settings.telegram_bot_token:
        print(f"[bot] No Telegram token — skipping alert for chat {chat_id}")
        return

    flag = FLAG_MAP.get(tender.country_code, "🌐")
    days_left = (tender.deadline - date.today()).days
    deadline_str = tender.deadline.strftime("%-d %B %Y")

    equipment = equipment_summary or tender.title
    budget_line = ""
    if tender.budget_usd:
        budget_line = f"\n💰 <b>Бюджет:</b> ~${tender.budget_usd:,.0f}"
    elif tender.budget_original and tender.currency_original:
        budget_line = f"\n💰 <b>Бюджет:</b> {tender.budget_original:,.0f} {tender.currency_original}"

    city_line = f"\n🏙 <b>Город:</b> {tender.city}" if tender.city else ""

    text = (
        f"🚨 <b>Новый тендер</b>\n\n"
        f"{flag} <b>Страна:</b> {tender.country_name}"
        f"{city_line}\n\n"
        f"📋 <b>Требуется:</b>\n{equipment}"
        f"{budget_line}\n\n"
        f"⏰ <b>Дедлайн:</b>\n{deadline_str} ({days_left} дн.)\n\n"
        f"🔗 <b>Официальная ссылка:</b>\n{tender.url}"
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
        )
        if resp.status_code != 200:
            print(f"[bot] Telegram error {resp.status_code}: {resp.text[:200]}")
