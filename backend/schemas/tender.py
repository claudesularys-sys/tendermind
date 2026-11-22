import uuid
from datetime import datetime, date
from pydantic import BaseModel


class TenderOut(BaseModel):
    id: uuid.UUID
    external_id: str
    source_id: str
    country_code: str
    country_name: str
    city: str | None
    title: str
    title_en: str | None
    equipment_summary: str | None
    budget_usd: float | None
    currency_original: str | None
    budget_original: float | None
    deadline: date
    is_active: bool
    url: str
    created_at: datetime
    vector_score: float | None = None  # injected from tender_matches

    model_config = {"from_attributes": True}


class TenderListResponse(BaseModel):
    items: list[TenderOut]
    total: int
    page: int
    per_page: int


class SourceStatusOut(BaseModel):
    source_id: str
    country_code: str
    country_name: str
    region: str
    last_run_at: datetime | None
    last_status: str | None
    last_fetched: int | None
    last_new: int | None
    schedule: str


class MapDataItem(BaseModel):
    country_code: str
    country_name: str
    count: int


class FavoriteOut(BaseModel):
    id: uuid.UUID
    tender: TenderOut
    note: str | None
    saved_at: datetime

    model_config = {"from_attributes": True}
