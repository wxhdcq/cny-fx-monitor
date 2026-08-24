import time as time_module
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation

import httpx

NON_FIAT_CODES = {"XAG", "XAU", "XDR", "XPD", "XPT"}


@dataclass(frozen=True)
class CurrencyInfo:
    code: str
    name: str
    symbol: str


@dataclass(frozen=True)
class RateQuote:
    code: str
    value_cny: Decimal
    observed_at: datetime
    source: str = "frankfurter"
    quote_kind: str = "central-bank-reference"
    is_cross_rate: bool = True


class FrankfurterProvider:
    def __init__(self, base_url: str, timeout: float = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def fetch_currencies(self) -> list[CurrencyInfo]:
        return self.parse_currencies(self._get_json("/currencies"))

    def fetch_rates(self, from_date: date | None = None) -> list[RateQuote]:
        params = {"base": "CNY"}
        if from_date is not None:
            params["from"] = from_date.isoformat()
        return self.parse_rates(self._get_json("/rates", params=params))

    def _get_json(self, path: str, params: dict[str, str] | None = None) -> list[dict]:
        last_error: httpx.HTTPError | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(f"{self.base_url}{path}", params=params)
                    response.raise_for_status()
                    return response.json()
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < 2:
                    time_module.sleep(0.5 * (2**attempt))
        assert last_error is not None
        raise last_error

    @staticmethod
    def parse_currencies(payload: list[dict]) -> list[CurrencyInfo]:
        result = []
        for item in payload:
            code = str(item.get("iso_code", "")).upper()
            if len(code) != 3 or code == "CNY" or code in NON_FIAT_CODES:
                continue
            result.append(
                CurrencyInfo(
                    code=code,
                    name=str(item.get("name", code)),
                    symbol=str(item.get("symbol") or ""),
                )
            )
        return result

    @staticmethod
    def parse_rates(payload: list[dict]) -> list[RateQuote]:
        result = []
        for item in payload:
            code = str(item.get("quote", "")).upper()
            try:
                foreign_per_cny = Decimal(str(item["rate"]))
                if (
                    foreign_per_cny <= 0
                    or len(code) != 3
                    or code == "CNY"
                    or code in NON_FIAT_CODES
                ):
                    continue
                value_cny = Decimal(1) / foreign_per_cny
                published = date.fromisoformat(str(item["date"]))
            except (KeyError, ValueError, InvalidOperation, ZeroDivisionError):
                continue
            result.append(
                RateQuote(
                    code=code,
                    value_cny=value_cny.quantize(Decimal("0.0000000001")),
                    observed_at=datetime.combine(published, time(16, 0), tzinfo=UTC),
                )
            )
        return result
