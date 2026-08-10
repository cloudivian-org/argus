"""Run the deterministic AML typology detectors over a customer."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from omnigent_client.tools import tool  # noqa: E402

from bankcore import api  # noqa: E402


@tool
def run_typology_checks(
    customer_id: str,
    lookback_days: int = 90,
    typology: str | None = None,
) -> dict:
    """
    Run the AML typology detectors and return their findings.

    Every figure a narrative may cite comes from here. The detectors are
    plain deterministic Python — structuring, funnel/pass-through,
    round-value trade wires, high-risk jurisdiction exposure, rapid
    in-and-out layering, profile deviation, behavioural break, and
    counterparty concentration. Each finding carries the exact
    transaction ids behind it so any number can be recomputed.

    Do not restate a number that no detector produced.

    :param customer_id: Customer to analyse.
    :param lookback_days: Analysis window ending at the sandbox as-of date.
    :param typology: Run a single named detector instead of all of them.
    :returns: Findings ordered with triggered, high-confidence ones first.
    """
    return api.typology_report(customer_id, lookback_days, typology)
