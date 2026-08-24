from decimal import Decimal

from app.detector import percentage_change, risk_score, severity_for_change


def test_percentage_change_for_depreciation() -> None:
    assert percentage_change(Decimal("0.18"), Decimal("0.20")) == Decimal("-10.00")


def test_percentage_change_handles_missing_baseline() -> None:
    assert percentage_change(Decimal(1), None) is None
    assert percentage_change(Decimal(1), Decimal(0)) is None


def test_high_risk_currency_uses_wider_warning_threshold() -> None:
    assert severity_for_change(Decimal("-4.9"), high_risk=True) is None
    assert severity_for_change(Decimal(-5), high_risk=True) == "warning"
    assert severity_for_change(Decimal(-10), high_risk=True) == "critical"


def test_major_currency_uses_tighter_threshold() -> None:
    assert severity_for_change(Decimal(-2), high_risk=False) == "warning"


def test_risk_score_is_bounded() -> None:
    assert risk_score(Decimal(-50), Decimal(-50), Decimal(-50), True) == 100
