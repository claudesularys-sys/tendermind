"""Celery tasks for crawlers and maintenance jobs."""
import asyncio
from celery import Celery
from celery.schedules import crontab
from core.config import settings

app = Celery("tendermind", broker=settings.redis_url, backend=settings.redis_url)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    timezone="UTC",
    beat_schedule={
        "crawl-all": {
            "task": "crawler.tasks.run_all_crawlers",
            "schedule": crontab(minute="*/30"),
        },
        "expire-tenders": {
            "task": "crawler.tasks.expire_tenders",
            "schedule": crontab(minute=5),  # top of each hour + 5 min
        },
    },
)


@app.task(name="crawler.tasks.run_all_crawlers", bind=True, max_retries=1)
def run_all_crawlers(self):
    from crawler.registry import get_all_crawlers
    crawlers = get_all_crawlers()
    print(f"[beat] Queuing {len(crawlers)} crawlers")
    for source_id in crawlers:
        run_crawler_task.delay(source_id)


@app.task(name="crawler.tasks.run_crawler_task", bind=True, max_retries=2)
def run_crawler_task(self, source_id: str):
    from crawler.registry import get_crawler
    from crawler.pipeline import process_tenders
    from core.database import AsyncSessionLocal
    from crud.tenders import log_crawler_run

    crawler = get_crawler(source_id)
    if not crawler:
        print(f"[task] Unknown source: {source_id}")
        return

    async def _run():
        # run() fetches tenders once and returns both result + tender list
        result, tenders = await crawler.run()

        if result.status == "ok" and tenders:
            # process_tenders awaits all AI matching before returning
            await process_tenders(tenders, result)

        # Log run to DB
        async with AsyncSessionLocal() as db:
            await log_crawler_run(db, {
                "source_id": result.source_id,
                "status": result.status,
                "fetched": result.fetched,
                "new_tenders": result.new_tenders,
                "matched": result.matched,
                "error_msg": result.error_msg,
                "duration_ms": result.duration_ms,
            })
            await db.commit()

        return result

    asyncio.run(_run())


@app.task(name="crawler.tasks.expire_tenders")
def expire_tenders():
    from crawler.pipeline import expire_old_tenders
    asyncio.run(expire_old_tenders())
