# TenderMind: AI tender monitor (prototype)

**Problem:** companies that sell equipment (in my case: power transformers) miss public tenders, because tenders are published on dozens of national portals in different languages.

**Solution:** TenderMind regularly collects new tenders from public portals, uses AI to keep only the ones that fit a company's profile, and sends an instant **Telegram alert** with the official link.

> Status: 🟡 prototype, built with Claude Code. Russian README: [README.ru.md](README.ru.md)

## How it works
1. **Crawlers** (one plugin per source) collect new tenders every 30 minutes: EU TED, UK Find a Tender, US SAM.gov, World Bank, UNGM, India GeM, Kazakhstan GosZakup, Russia Zakupki.
2. **AI matching:** each tender is compared with the company profile (embeddings + a quick check by Claude).
3. **Alert:** matching tenders are sent to Telegram; a web dashboard shows the list.

## Tech stack
Python 3.12 · FastAPI · async SQLAlchemy · Celery + Redis · PostgreSQL · Qdrant (vector search) · Claude API · aiogram (Telegram bot) · Next.js dashboard · Docker Compose

## Run locally
```bash
cp .env.example .env   # add your own API keys
docker-compose up -d
cd frontend && npm install && npm run dev
```
API docs: http://localhost:8000/docs

## Add a new source
Create one file in `backend/crawler/sources/<region>/`, extend `BaseCrawler`, implement `fetch_tenders()`. It is picked up automatically.
