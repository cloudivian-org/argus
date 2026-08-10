"""Query the transaction ledger for a customer."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from omnigent_client.tools import tool  # noqa: E402

from bankcore import api  # noqa: E402


@tool
def get_transactions(
    customer_id: str,
    lookback_days: int = 90,
    direction: str | None = None,
    min_amount: float | None = None,
    account_id: str | None = None,
    channel: str | None = None,
) -> dict:
    """
    Return a customer's transactions with an aggregate summary.

    Use this to pull the specific ledger entries that will be cited as
    evidence. The response always includes aggregates computed over the
    full match set, even when the returned rows are truncated, so ask
    for a narrow slice rather than the whole ledger.

    :param customer_id: Customer whose accounts to query.
    :param lookback_days: Window ending at the sandbox as-of date.
    :param direction: ``credit`` (money in) or ``debit`` (money out).
    :param min_amount: Minimum transaction amount.
    :param account_id: Restrict to a single account.
    :param channel: Restrict to one channel, e.g. ``wire``,
        ``branch_cash``, ``p2p``, ``atm``, ``crypto_exchange``.
    :returns: Matching rows plus totals by direction, channel, and country.
    """
    return api.transactions_query(
        customer_id,
        lookback_days=lookback_days,
        direction=direction,
        min_amount=min_amount,
        account_id=account_id,
        channel=channel,
    )
