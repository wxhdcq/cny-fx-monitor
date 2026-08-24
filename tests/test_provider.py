from decimal import Decimal

from app.providers import FrankfurterProvider


def test_parse_rates_inverts_cny_base_quote() -> None:
    payload = [{"date": "2026-08-24", "base": "CNY", "quote": "TRY", "rate": 5}]
    quotes = FrankfurterProvider.parse_rates(payload)
    assert len(quotes) == 1
    assert quotes[0].code == "TRY"
    assert quotes[0].value_cny == Decimal("0.2000000000")


def test_parse_rates_skips_invalid_values() -> None:
    payload = [
        {"date": "2026-08-24", "quote": "BAD", "rate": 0},
        {"date": "not-a-date", "quote": "USD", "rate": 1},
    ]
    assert FrankfurterProvider.parse_rates(payload) == []


def test_non_fiat_assets_are_excluded() -> None:
    payload = [
        {"date": "2026-08-24", "quote": "XAU", "rate": 0.0002},
        {"date": "2026-08-24", "quote": "USD", "rate": 0.15},
    ]
    quotes = FrankfurterProvider.parse_rates(payload)
    assert [quote.code for quote in quotes] == ["USD"]
