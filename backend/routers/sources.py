from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.security import get_current_user
from crud.tenders import get_latest_runs, get_map_data, log_crawler_run
from schemas.tender import SourceStatusOut, MapDataItem
from models.user import User

router = APIRouter(tags=["sources & analytics"])


@router.get("/sources", response_model=list[SourceStatusOut])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from crawler.registry import get_all_crawlers
    crawlers = get_all_crawlers()
    latest_runs = {r.source_id: r for r in await get_latest_runs(db)}

    result = []
    for source_id, crawler in sorted(crawlers.items()):
        run = latest_runs.get(source_id)
        result.append(SourceStatusOut(
            source_id=source_id,
            country_code=crawler.country_code,
            country_name=crawler.country_name,
            region=crawler.region,
            last_run_at=run.ran_at if run else None,
            last_status=run.status if run else None,
            last_fetched=run.fetched if run else None,
            last_new=run.new_tenders if run else None,
            schedule=crawler.schedule,
        ))
    return result


@router.post("/sources/{source_id}/trigger")
async def trigger_source(
    source_id: str,
    current_user: User = Depends(get_current_user),
):
    from crawler.registry import get_crawler
    from crawler.tasks import run_crawler_task
    crawler = get_crawler(source_id)
    if not crawler:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found")
    run_crawler_task.delay(source_id)
    return {"queued": True, "source_id": source_id}


@router.get("/analytics/map", response_model=list[MapDataItem])
async def map_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_map_data(db)
