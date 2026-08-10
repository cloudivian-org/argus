"""Read-only access layer over the synthetic core-banking sandbox.

Every tool reaches the data through this module so there is exactly one
place that decides what a "customer record" or a "transaction" looks
like. In a real deployment this file is the seam you replace: swap the
JSON loaders for calls to the core banking platform, the KYC master, and
the case-management system, and nothing above this layer changes.

The layer is deliberately read-only for customer and transaction data.
Nothing an agent does can mutate a customer record or a ledger entry.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CASEFILE_DIR = ROOT / "casefiles"

# The sandbox is a point-in-time snapshot; "today" is fixed so demo runs
# are reproducible and relative-date evidence never drifts.
AS_OF = date(2026, 8, 1)


@lru_cache(maxsize=None)
def _load(name: str) -> Any:
    """Load and cache one JSON dataset file."""
    path = DATA_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Sandbox dataset {name}.json is missing. "
            f"Run `python3 scripts/generate_data.py` first."
        )
    return json.loads(path.read_text())


def customers() -> list[dict]:
    """Return every customer record."""
    return _load("customers")


def accounts() -> list[dict]:
    """Return every account record."""
    return _load("accounts")


def transactions() -> list[dict]:
    """Return every transaction record."""
    return _load("transactions")


def alerts() -> list[dict]:
    """Return every transaction-monitoring alert."""
    return _load("alerts")


def watchlist() -> list[dict]:
    """Return every sanctions / PEP / internal watchlist entry."""
    return _load("watchlist")


def adverse_media() -> list[dict]:
    """Return the simulated adverse-media corpus."""
    return _load("adverse_media")


def prior_cases() -> list[dict]:
    """Return closed investigation history."""
    return _load("prior_cases")


def jurisdictions() -> dict[str, dict]:
    """Return the country risk reference table."""
    return _load("jurisdictions")


# ── lookups ──────────────────────────────────────────────────────────


def get_customer(customer_id: str) -> dict | None:
    """Return one customer record, or ``None`` if unknown."""
    return next((c for c in customers() if c["customer_id"] == customer_id), None)


def get_alert(alert_id: str) -> dict | None:
    """Return one alert record, or ``None`` if unknown."""
    return next((a for a in alerts() if a["alert_id"] == alert_id), None)


def accounts_for(customer_id: str) -> list[dict]:
    """Return every account belonging to a customer."""
    return [a for a in accounts() if a["customer_id"] == customer_id]


def country_risk(code: str) -> str:
    """Return the risk band for a country code (``unknown`` if absent)."""
    return jurisdictions().get(code, {}).get("risk", "unknown")


def txns_for(
    customer_id: str,
    *,
    lookback_days: int | None = None,
    account_id: str | None = None,
    min_amount: float | None = None,
    direction: str | None = None,
) -> list[dict]:
    """
    Return a customer's transactions, newest first, with optional filters.

    :param customer_id: Owning customer.
    :param lookback_days: Only transactions booked within this many days
        of the sandbox as-of date.
    :param account_id: Restrict to one account.
    :param min_amount: Minimum absolute amount.
    :param direction: ``credit`` (money in) or ``debit`` (money out).
    :returns: Matching transaction records sorted newest first.
    """
    account_ids = {a["account_id"] for a in accounts_for(customer_id)}
    if account_id:
        account_ids &= {account_id}
    cutoff = AS_OF - timedelta(days=lookback_days) if lookback_days else None

    out = []
    for t in transactions():
        if t["account_id"] not in account_ids:
            continue
        if cutoff and _as_date(t["booking_date"]) < cutoff:
            continue
        if min_amount is not None and t["amount"] < min_amount:
            continue
        if direction and t["direction"] != direction:
            continue
        out.append(t)
    out.sort(key=lambda t: t["booking_date"], reverse=True)
    return out


def _as_date(value: str) -> date:
    """Parse an ISO date string."""
    return datetime.strptime(value, "%Y-%m-%d").date()


def days_ago(value: str) -> int:
    """Return how many days before the as-of date a booking date falls."""
    return (AS_OF - _as_date(value)).days
