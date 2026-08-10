"""Retrieve prior investigation history for a customer."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omnigent_client.tools import tool  # noqa: E402

from bankcore import api  # noqa: E402


@tool
def get_prior_cases(customer_id: str) -> dict:
    """
    Return closed investigations and prior SAR history for a customer.

    History changes the meaning of a repeat alert. The same rule firing a
    second time — especially where a previously agreed remediation was
    never completed — is materially more serious than a first occurrence,
    and a prior SAR obliges the bank to consider a continuing-activity
    report.

    :param customer_id: Customer whose case history to retrieve.
    :returns: Prior cases, prior SAR count, and outstanding follow-ups.
    """
    return api.prior_case_history(customer_id)
