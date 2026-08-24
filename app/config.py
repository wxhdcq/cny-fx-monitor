import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    database_url: str
    collect_interval_minutes: int
    request_timeout_seconds: float
    frankfurter_base_url: str
    admin_token: str
    telegram_bot_token: str
    telegram_chat_id: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/fx-monitor.db"),
        collect_interval_minutes=max(5, int(os.getenv("COLLECT_INTERVAL_MINUTES", "60"))),
        request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
        frankfurter_base_url=os.getenv(
            "FRANKFURTER_BASE_URL", "https://api.frankfurter.dev/v2"
        ).rstrip("/"),
        admin_token=os.getenv("ADMIN_TOKEN", ""),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
    )
