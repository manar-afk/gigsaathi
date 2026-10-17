"""Deterministic earnings maths. The LLM never computes totals."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from app.schemas import EntryIn, Period

_CENT = Decimal("0.01")


@dataclass(frozen=True)
class Summary:
    income: Decimal
    expense: Decimal
    net: Decimal
    trips: int
    hours: Decimal
    income_per_hour: Decimal | None
    entries: int

    def as_dict(self) -> dict:
        return {
            "income": float(self.income), "expense": float(self.expense),
            "net": float(self.net), "trips": self.trips, "hours": float(self.hours),
            "income_per_hour": None if self.income_per_hour is None else float(self.income_per_hour),
            "entries": self.entries,
        }


def period_start(period: Period, today: date) -> date | None:
    """Start date for a period; 'week' means the last 7 days including today."""
    if period == "today":
        return today
    if period == "week":
        return today - timedelta(days=6)
    if period == "month":
        return today.replace(day=1)
    return None


def to_record(entry: EntryIn, today: date) -> dict:
    """Convert a validated entry to a storable record; bad/future dates become today."""
    try:
        day = date.fromisoformat(entry.date) if entry.date else today
    except ValueError:
        day = today
    if day > today:
        day = today
    return {
        "type": entry.type, "amount": round(entry.amount, 2),
        "category": entry.category.strip().lower() or "other",
        "trips": entry.trips, "hours": entry.hours, "date": day.isoformat(),
    }


def summarise(records: Iterable[dict]) -> Summary:
    income = expense = hours = Decimal(0)
    trips = count = 0
    for r in records:
        amount = Decimal(str(r["amount"]))
        count += 1
        if r["type"] == "income":
            income += amount
            trips += int(r.get("trips") or 0)
        else:
            expense += amount
        hours += Decimal(str(r.get("hours") or 0))
    per_hour = (income / hours).quantize(_CENT, ROUND_HALF_UP) if hours > 0 else None
    return Summary(income, expense, income - expense, trips, hours, per_hour, count)
