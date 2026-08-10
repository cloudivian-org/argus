"""Compute the deterministic risk scorecard for an alert."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omnigent_client.tools import tool  # noqa: E402

from bankcore import scoring  # noqa: E402


@tool
def score_alert_risk(alert_id: str, lookback_days: int | None = None) -> dict:
    """
    Score an alert against the bank's fixed AML scorecard.

    The scorecard runs every detector, screens the customer's whole
    counterparty network, and adds static customer risk and case history,
    with per-category ceilings so no single signal saturates the total.
    Weights live in version-controlled code, so the score is
    reproducible, testable, and defensible to a model-risk reviewer in a
    way a model's own judgement is not.

    The banded recommendation is advisory. Departing from it is allowed
    and sometimes correct — but the departure and its reasoning must be
    written into the disposition.

    :param alert_id: Alert to score.
    :param lookback_days: Override the alert's own lookback window.
    :returns: Score, band, recommended disposition, and every
        contributing factor with the evidence behind it.
    """
    try:
        return scoring.score_alert(alert_id, lookback_days)
    except ValueError as exc:
        return {"error": str(exc)}
