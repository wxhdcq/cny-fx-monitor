from decimal import Decimal


def percentage_change(current: Decimal, previous: Decimal | None) -> Decimal | None:
    if previous is None or previous == 0:
        return None
    return ((current - previous) / previous * Decimal(100)).quantize(Decimal("0.01"))


def severity_for_change(change_24h: Decimal | None, high_risk: bool) -> str | None:
    if change_24h is None or change_24h >= 0:
        return None
    drop = abs(change_24h)
    warning = Decimal(5) if high_risk else Decimal(2)
    critical = Decimal(10) if high_risk else Decimal(5)
    if drop >= critical:
        return "critical"
    if drop >= warning:
        return "warning"
    return None


def risk_score(
    change_24h: Decimal | None,
    change_7d: Decimal | None,
    change_30d: Decimal | None,
    high_risk: bool,
) -> int:
    score = 12 if high_risk else 0
    for change, weight, cap in (
        (change_24h, Decimal(3), 30),
        (change_7d, Decimal("1.5"), 30),
        (change_30d, Decimal("0.8"), 28),
    ):
        if change is not None and change < 0:
            score += min(cap, int(abs(change) * weight))
    return min(100, score)
