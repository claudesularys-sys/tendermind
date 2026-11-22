import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    telegram_id: int | None
    notif_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CompanyProfileIn(BaseModel):
    company_name: str = ""
    transformer_types: list[str] = []
    power_kva_min: int | None = None
    power_kva_max: int | None = None
    voltage_kv: list[str] = []
    certifications: list[str] = []
    max_delivery_days: int | None = None
    target_countries: list[str] = []
    min_budget_usd: float | None = None
    keywords_extra: list[str] = []


class CompanyProfileOut(CompanyProfileIn):
    id: uuid.UUID
    user_id: uuid.UUID
    profile_vector_id: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}
