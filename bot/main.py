"""
TenderMind Telegram Bot
- /start — link Telegram account to TenderMind profile
- /status — show monitoring status
- /pause / /resume — toggle notifications
- /help — help message
"""
import asyncio
import os
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import httpx

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API_BASE = os.getenv("BACKEND_URL", "http://backend:8000")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)


@router.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        "👋 <b>Добро пожаловать в TenderMind!</b>\n\n"
        "Я нахожу тендеры на трансформаторы по всему миру и мгновенно сообщаю вам.\n\n"
        "Чтобы получать уведомления:\n"
        "1️⃣ Зарегистрируйтесь на tendermind.ai\n"
        "2️⃣ В настройках введите ваш Telegram ID: <code>"
        f"{message.from_user.id}</code>\n\n"
        "Или отправьте <b>ваш JWT токен</b> командой:\n"
        "<code>/link ВАШ_ТОКЕН</code>"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("link"))
async def cmd_link(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: <code>/link ВАШ_JWT_ТОКЕН</code>", parse_mode="HTML")
        return

    token = parts[1].strip()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{API_BASE}/v1/auth/telegram/link",
                params={
                    "telegram_id": message.from_user.id,
                    "chat_id": message.chat.id,
                },
                headers={"Authorization": f"Bearer {token}"},
            )
        if resp.status_code == 200:
            await message.answer(
                "✅ <b>Telegram успешно подключён!</b>\n\n"
                "Теперь вы будете получать уведомления о новых тендерах.",
                parse_mode="HTML",
            )
        else:
            await message.answer("❌ Токен недействителен. Проверьте токен на tendermind.ai")
    except Exception as e:
        await message.answer(f"❌ Ошибка подключения к серверу: {e}")


@router.message(Command("status"))
async def cmd_status(message: Message):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{API_BASE}/health")
        status = "🟢 Онлайн" if resp.status_code == 200 else "🔴 Проблемы"
    except Exception:
        status = "🔴 Недоступен"

    await message.answer(
        f"📡 <b>Статус TenderMind</b>\n\n"
        f"API: {status}\n"
        f"Мониторинг: 40+ источников по всему миру\n"
        f"Интервал: каждые 30 минут",
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Команды TenderMind</b>\n\n"
        "/start — начало работы\n"
        "/link ТОКЕН — привязать аккаунт\n"
        "/status — статус системы\n"
        "/help — справка\n\n"
        "🌐 Личный кабинет: tendermind.ai",
        parse_mode="HTML",
    )


@router.message(F.text)
async def unknown(message: Message):
    await message.answer(
        "Используйте /help для списка команд.",
        parse_mode="HTML",
    )


async def main():
    print(f"[bot] Starting TenderMind bot...")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
