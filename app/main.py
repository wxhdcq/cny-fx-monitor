import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .config import get_settings
from .database import SessionLocal, init_database
from .models import Alert, Rate, SourceStatus
from .services import build_rate_snapshot, run_collection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
settings = get_settings()
scheduler = BackgroundScheduler(timezone="UTC")
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    scheduler.add_job(run_collection, "date", id="initial-collection", replace_existing=True)
    scheduler.add_job(
        run_collection,
        "interval",
        minutes=settings.collect_interval_minutes,
        id="rate-collection",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="人民币汇率监测器", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    with SessionLocal() as session:
        source = session.get(SourceStatus, "frankfurter")
        return {
            "status": "ok" if source is None or source.status != "error" else "degraded",
            "database": "ok",
            "source": source.status if source else "initializing",
            "last_success_at": source.last_success_at.isoformat()
            if source and source.last_success_at
            else None,
        }


@app.get("/api/rates")
def rates(
    tag: str = Query("all", pattern="^(all|major|low-price|high-risk)$"),
    q: str = Query("", max_length=50),
) -> dict:
    with SessionLocal() as session:
        items = build_rate_snapshot(session)
    if tag != "all":
        field = {"major": "is_major", "low-price": "is_low_price", "high-risk": "is_high_risk"}[tag]
        items = [item for item in items if item[field]]
    if q:
        needle = q.casefold()
        items = [
            item
            for item in items
            if needle in item["code"].casefold()
            or needle in item["name_en"].casefold()
            or needle in item["name_zh"].casefold()
        ]
    items.sort(key=lambda item: (not item["is_major"], item["code"]))
    return {"items": items, "count": len(items)}


@app.get("/api/summary")
def summary() -> dict:
    with SessionLocal() as session:
        items = build_rate_snapshot(session)
        alerts_count = len(session.scalars(select(Alert).where(Alert.status == "open")).all())
        source = session.get(SourceStatus, "frankfurter")
    movers = [item for item in items if item["change_1d"] is not None]
    movers.sort(key=lambda item: item["change_1d"])
    return {
        "currency_count": len(items),
        "high_risk_count": sum(item["is_high_risk"] for item in items),
        "open_alerts": alerts_count,
        "last_updated": max((item["observed_at"] for item in items), default=None),
        "source": {
            "name": "Frankfurter",
            "status": source.status if source else "initializing",
            "currency_count": source.currency_count if source else 0,
            "last_success_at": source.last_success_at.isoformat()
            if source and source.last_success_at
            else None,
        },
        "top_drops": movers[:5],
    }


@app.get("/api/rates/{code}/history")
def history(code: str, days: int = Query(90, ge=7, le=3650)) -> dict:
    code = code.upper()
    cutoff = datetime.now(UTC) - timedelta(days=days)
    with SessionLocal() as session:
        rows = session.scalars(
            select(Rate)
            .where(Rate.currency_code == code, Rate.observed_at >= cutoff)
            .order_by(Rate.observed_at)
        ).all()
    if not rows:
        raise HTTPException(404, "没有该货币的历史数据")
    return {
        "code": code,
        "points": [
            {
                "time": row.observed_at.isoformat(),
                "value": float(row.value_cny),
                "source": row.source,
            }
            for row in rows
        ],
    }


@app.get("/api/alerts")
def alerts() -> dict:
    with SessionLocal() as session:
        rows = session.scalars(select(Alert).order_by(Alert.updated_at.desc()).limit(100)).all()
    return {
        "items": [
            {
                "id": row.id,
                "currency_code": row.currency_code,
                "severity": row.severity,
                "message": row.message,
                "status": row.status,
                "updated_at": row.updated_at.isoformat(),
            }
            for row in rows
        ]
    }


@app.post("/api/collect")
def collect(x_admin_token: str = Header("")) -> dict:
    if not settings.admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(401, "管理员令牌无效")
    return run_collection()
