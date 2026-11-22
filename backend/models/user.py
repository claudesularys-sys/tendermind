import uuid
from datetime import datetime, UTC
from sqlalchemy import String, Boolean, DateTime, BigInteger, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, unique=True)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    notif_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True, unique=True)
    company_name: Mapped[str] = mapped_column(Text, nullable=False, default="")
    transformer_types: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    power_kva_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    power_kva_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    voltage_kv: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    certifications: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    max_delivery_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_countries: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    min_budget_usd: Mapped[float | None] = mapped_column(Numeric(precision=14, scale=2), nullable=True)
    keywords_extra: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    profile_vector_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
