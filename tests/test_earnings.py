from datetime import date
from decimal import Decimal

from app.schemas import EntryIn
from app.services.earnings import period_start, summarise, to_record


def test_summarise_totals_and_rate():
    rows = [
        {"type": "income", "amount": 850, "trips": 3, "hours": 5},
        {"type": "income", "amount": 150.5, "trips": 1, "hours": None},
        {"type": "expense", "amount": 200, "trips": None, "hours": None},
    ]
    s = summarise(rows)
    assert (s.income, s.expense, s.net) == (Decimal("1000.5"), Decimal(200), Decimal("800.5"))
    assert s.trips == 4 and s.income_per_hour == Decimal("200.10")


def test_no_hours_means_no_rate():
    assert summarise([{"type": "income", "amount": 10}]).income_per_hour is None


def test_period_start(today):
    assert period_start("today", today) == today
    assert period_start("week", today) == date(2026, 10, 11)
    assert period_start("month", today) == date(2026, 10, 1)
    assert period_start("all", today) is None


def test_future_or_bad_date_becomes_today(today):
    e = EntryIn(type="income", amount=10, date="2030-01-01")
    assert to_record(e, today)["date"] == today.isoformat()
    e = EntryIn(type="income", amount=10, date="not-a-date")
    assert to_record(e, today)["date"] == today.isoformat()
