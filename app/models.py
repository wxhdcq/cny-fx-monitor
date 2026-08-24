from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Currency(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name_en: Mapped[str] = mapped_column(String(120))
    name_zh: Mapped[str] = mapped_column(String(80), default="")
    symbol: Mapped[str] = mapped_column(String(16), default="")
    is_major: Mapped[bool] = mapped_column(Boolean, default=False)
    is_low_price: Mapped[bool] = mapped_column(Boolean, default=False)
    is_high_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Rate(Base):
    __tablename__ = "rates"
    __table_args__ = (
        UniqueConstraint("currency_code", "source", "observed_at", name="uq_rate_observation"),
        Index("ix_rates_currency_observed", "currency_code", "observed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"), index=True)
    value_cny: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    source: Mapped[str] = mapped_column(String(40))
    quote_kind: Mapped[str] = mapped_column(String(40), default="reference")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_cross_rate: Mapped[bool] = mapped_column(Boolean, default=True)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alerts_status_updated", "status", "updated_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    currency_code: Mapped[str] = mapped_column(ForeignKey("currencies.code"), index=True)
    alert_type: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    metric_value: Mapped[Decimal | None] = mapped_column(Numeric(16, 4), nullable=True)
    threshold: Mapped[Decimal | None] = mapped_column(Numeric(16, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="open")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SourceStatus(Base):
    __tablename__ = "source_status"

    source: Mapped[str] = mapped_column(String(40), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="unknown")
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    currency_count: Mapped[int] = mapped_column(default=0)
