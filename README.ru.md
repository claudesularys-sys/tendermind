# TenderMind — Global AI Tender Monitor

Автоматически сканирует 40+ стран → AI фильтрует только подходящие тендеры → мгновенный алерт в Telegram.

## Быстрый старт

### 1. Настройка окружения

```bash
cp .env.example .env
# Заполните .env:
# ANTHROPIC_API_KEY, OPENAI_API_KEY, TELEGRAM_BOT_TOKEN
# SAM_GOV_API_KEY (опционально, для США)
```

### 2. Запуск backend + bot (Docker)

```bash
docker-compose up -d
```

Это запустит:
- **PostgreSQL 16** (порт 5432)
- **Redis 7** (порт 6379)
- **Qdrant** vector DB (порт 6333)
- **FastAPI** backend (порт 8000)
- **Celery worker** — запускает краулеры
- **Celery beat** — планировщик (каждые 30 мин)
- **Telegram bot**

### 3. Запуск frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### 4. Первый вход

1. Откройте http://localhost:3000/auth
2. Зарегистрируйтесь
3. Заполните профиль компании (http://localhost:3000/settings/profile)
4. В Telegram боте (@ваш_бот): `/link ВАШ_JWT_ТОКЕН`

Система начнёт присылать уведомления как только найдёт подходящий тендер.

## Добавление нового источника (за 2-3 часа)

```bash
# Создайте файл в нужном регионе:
touch backend/crawler/sources/asia/new_source.py
```

Реализуйте класс:
```python
from crawler.base import BaseCrawler, TenderCreate

class NewSourceCrawler(BaseCrawler):
    source_id = "new_source"
    country_code = "XX"
    country_name = "Country Name"
    region = "asia"
    schedule = "*/30 * * * *"

    async def fetch_tenders(self) -> list[TenderCreate]:
        # ваша логика
        ...
```

Краулер **автоматически** подхватится при следующем перезапуске.

## API документация

После запуска: http://localhost:8000/docs

## Структура проекта

```
tendermind/
├── backend/
│   ├── crawler/sources/    ← плагины для каждого источника
│   │   ├── americas/       ← США, Канада, Бразилия...
│   │   ├── europe/         ← TED EU, UK, Германия...
│   │   ├── asia/           ← Индия, Австралия, Корея...
│   │   ├── cis/            ← Казахстан, Россия...
│   │   ├── mena/           ← ОАЭ, Саудовская Аравия...
│   │   └── international/  ← World Bank, UNGM, EBRD...
│   ├── ai/                 ← embedder, analyzer (Claude)
│   ├── bot/                ← Telegram sender
│   └── routers/            ← FastAPI endpoints
├── bot/                    ← aiogram Telegram bot
└── frontend/               ← Next.js 14 dashboard
```
