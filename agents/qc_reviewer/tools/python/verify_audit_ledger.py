"""Verify the tamper-evident audit ledger and summarise the case file."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from omnigent_client.tools import tool  # noqa: E402

from bankcore import casefile  # noqa: E402


@tool
def verify_audit_ledger(alert_id: str | None = None) -> dict:
    """
    Re-walk the audit ledger's hash chain and report its integrity.

    Every write the agent makes appends an entry carrying the SHA-256 of
    the entry before it. Altering or removing any historical entry breaks
    verification for everything after it. This is what turns "the AI did
    the work" into evidence a supervisor or an external examiner can
    actually rely on.

    :param alert_id: Optionally also return that alert's case file.
    :returns: The verification report, and the case file if requested.
    """
    report = casefile.verify_ledger()
    report["summary"] = (
        ("AUDIT LEDGER INTACT" if report["verified"] else "AUDIT LEDGER INTEGRITY FAILURE")
        + f" — {report.get('entries', 0)} entry(ies) verified. {report.get('note', '')}"
        + (
            f" First broken link at index {report['broken_at_index']}."
            if not report["verified"] else ""
        )
    )
    if alert_id:
        report["case_file"] = casefile.read_case(alert_id)
        report["case_file_found"] = report["case_file"] is not None
    return report
