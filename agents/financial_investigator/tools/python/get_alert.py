"""Retrieve one transaction-monitoring alert with its immediate context."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from omnigent_client.tools import tool  # noqa: E402

from bankcore import api  # noqa: E402


@tool
def get_alert(alert_id: str) -> dict:
    """
    Fetch a transaction-monitoring alert and the accounts it covers.

    This is the entry point for a triage run. It returns what the
    monitoring system saw — the rule that fired, its threshold, the
    scored priority, and any branch narrative attached to the alert —
    without any interpretation.

    :param alert_id: Alert identifier, e.g. ``ALT-2026-0113``.
    :returns: The alert record plus a thumbnail of the subject customer
        and the accounts in scope.
    """
    return api.alert_context(alert_id)
