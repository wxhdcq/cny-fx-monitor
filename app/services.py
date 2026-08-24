import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .currencies import ZH_NAMES, flag_for, flags_for
from .database import SessionLocal
from .detector import percentage_change, risk_score, severity_for_change
from .models import Alert, Currency, Rate, SourceStatus
from .providers import FrankfurterProvider

logger = logging.getLogger(__name__)
settings = get_settings()


def _provider() -> FrankfurterProvider:
    return FrankfurterProvider(settings.frankfurter_base_url, settings.request_timeout_seconds)


def sync_currencies(session: Session, provider: FrankfurterProvider) -> int:
    currencies = provider.fetch_currencies()
    for existing in session.scalars(select(Currency)).all():
        existing.is_active = False
    for item in currencies:
        currency = session.get(Currency, item.code)
        flags = flags_for(item.code)
        if currency is None:
            currency = Currency(code=item.code, name_en=item.name)
            session.add(currency)
        currency.name_en = item.name
        currency.name_zh = ZH_NAMES.get(item.code, "")
        currency.symbol = item.symbol
        currency.is_active = True
        currency.is_major = flags["is_major"]
        currency.is_low_price = flags["is_low_price"]
        currency.is_high_risk = flags["is_high_risk"]
    session.commit()
    return len(currencies)


def _upsert_source_status(
    session: Session, status: str, now: datetime, count: int = 0, error: str = ""
) -> None:
    row = session.get(SourceStatus, "frankfurter") or SourceStatus(source="frankfurter")
    session.add(row)
    row.status = status
    row.last_attempt_at = now
    row.last_error = error[:1000]
    if status == "healthy":
        row.last_success_at = now
        row.currency_count = count
    session.commit()


def run_collection() -> dict:
    now = datetime.now(UTC)
    provider = _provider()
    with SessionLocal() as session:
        try:
            if session.scalar(select(Currency.code).limit(1)) is None:
                sync_currencies(session, provider)
            earliest_observation = session.scalar(select(func.min(Rate.observed_at)))
            if earliest_observation and earliest_observation.tzinfo is None:
                earliest_observation = earliest_observation.replace(tzinfo=UTC)
            needs_backfill = earliest_observation is None or earliest_observation > now - timedelta(
                days=365
            )
            from_date = (now - timedelta(days=370)).date() if needs_backfill else None
            quotes = provider.fetch_rates(from_date=from_date)
            known = set(
                session.scalars(select(Currency.code).where(Currency.is_active.is_(True))).all()
            )
            inserted = 0
            for quote in quotes:
                if quote.code not in known:
                    continue
                exists = session.scalar(
                    select(Rate.id).where(
                        Rate.currency_code == quote.code,
                        Rate.source == quote.source,
                        Rate.observed_at == quote.observed_at,
                    )
                )
                if exists:
                    continue
                session.add(
                    Rate(
                        currency_code=quote.code,
                        value_cny=quote.value_cny,
                        source=quote.source,
                        quote_kind=quote.quote_kind,
                        observed_at=quote.observed_at,
                        fetched_at=now,
                        is_cross_rate=quote.is_cross_rate,
                    )
                )
                inserted += 1
            session.commit()
            currency_count = len({quote.code for quote in quotes})
            _upsert_source_status(session, "healthy", now, currency_count)
            generated = evaluate_alerts(session)
            logger.info(
                "collection complete quotes=%s inserted=%s alerts=%s",
                len(quotes),
                inserted,
                generated,
            )
            return {
                "quotes": len(quotes),
                "inserted": inserted,
                "alerts": generated,
                "backfilled": needs_backfill,
            }
        except Exception as exc:
            session.rollback()
            _upsert_source_status(session, "error", now, error=str(exc))
            logger.exception("rate collection failed")
            raise


def _series_by_currency(session: Session, days: int = 370) -> dict[str, list[Rate]]:
    cutoff = datetime.now(UTC) - timedelta(days=days + 2)
    rates = session.scalars(
        select(Rate)
        .where(Rate.observed_at >= cutoff)
        .order_by(Rate.currency_code, Rate.observed_at)
    ).all()
    grouped: dict[str, list[Rate]] = defaultdict(list)
    for rate in rates:
        grouped[rate.currency_code].append(rate)
    return grouped


def _previous_value(series: list[Rate], target: datetime) -> Decimal | None:
    candidates = [rate for rate in series if rate.observed_at <= target]
    return candidates[-1].value_cny if candidates else None


def build_rate_snapshot(session: Session) -> list[dict]:
    currencies = {
        item.code: item
        for item in session.scalars(select(Currency).where(Currency.is_active.is_(True))).all()
    }
    grouped = _series_by_currency(session)
    items = []
    for code, series in grouped.items():
        if not series or code not in currencies:
            continue
        latest = series[-1]
        changes = {}
        for key, days in (
            ("change_1d", 1),
            ("change_7d", 7),
            ("change_30d", 30),
            ("change_90d", 90),
            ("change_180d", 180),
            ("change_365d", 365),
        ):
            changes[key] = percentage_change(
                latest.value_cny, _previous_value(series, latest.observed_at - timedelta(days=days))
            )
        currency = currencies[code]
        score = risk_score(
            changes["change_1d"], changes["change_7d"], changes["change_30d"], currency.is_high_risk
        )
        items.append(
            {
                "code": code,
                "name_zh": currency.name_zh,
                "name_en": currency.name_en,
                "symbol": currency.symbol,
                "flag": flag_for(code),
                "value_cny": float(latest.value_cny),
                "observed_at": latest.observed_at.isoformat(),
                "source": latest.source,
                "quote_kind": latest.quote_kind,
                "is_major": currency.is_major,
                "is_low_price": currency.is_low_price,
                "is_high_risk": currency.is_high_risk,
                "risk_score": score,
                **{
                    key: float(value) if value is not None else None
                    for key, value in changes.items()
                },
            }
        )
    return items


def evaluate_alerts(session: Session) -> int:
    generated = 0
    for item in build_rate_snapshot(session):
        change = Decimal(str(item["change_1d"])) if item["change_1d"] is not None else None
        severity = severity_for_change(change, item["is_high_risk"])
        if severity is None:
            continue
        existing = session.scalar(
            select(Alert).where(
                Alert.currency_code == item["code"],
                Alert.alert_type == "daily_drop",
                Alert.status == "open",
            )
        )
        now = datetime.now(UTC)
        threshold = Decimal(5) if item["is_high_risk"] else Decimal(2)
        if existing:
            existing.updated_at = now
            existing.severity = severity
            continue
        alert = Alert(
            currency_code=item["code"],
            alert_type="daily_drop",
            severity=severity,
            message=f"{item['code']} 24小时相对人民币下跌 {abs(change):.2f}%",
            metric_value=change,
            threshold=threshold,
            opened_at=now,
            updated_at=now,
        )
        session.add(alert)
        generated += 1
        send_telegram(alert.message, severity)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
    return generated


def send_telegram(message: str, severity: str) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    try:
        httpx.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            json={"chat_id": settings.telegram_chat_id, "text": f"[{severity.upper()}] {message}"},
            timeout=10,
        ).raise_for_status()
    except httpx.HTTPError:
        logger.exception("telegram notification failed")
