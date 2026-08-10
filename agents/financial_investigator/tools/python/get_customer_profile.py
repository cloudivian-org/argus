"""Retrieve the KYC/CDD profile that activity must be judged against."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from omnigent_client.tools import tool  # noqa: E402

from bankcore import api  # noqa: E402


@tool
def get_customer_profile(customer_id: str) -> dict:
    """
    Fetch the KYC profile, accounts, and declared expectations for a customer.

    Suspicion is always relative to what the bank was told to expect.
    This returns that baseline: occupation or industry, declared source
    of funds, expected turnover, beneficial ownership, and how stale the
    last periodic review has become.

    :param customer_id: Customer identifier, e.g. ``CUS-1007``.
    :returns: The customer record with accounts and a KYC currency check.
    """
    return api.customer_profile(customer_id)
