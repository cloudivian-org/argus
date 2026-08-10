"""Submit a SAR narrative draft for mandatory human review.

This tool cannot file anything. It parks a draft in
``pending_human_review`` and records the fact in the audit ledger. The
filing decision, and the filing itself, stay with a qualified human in
the bank's own reporting system.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omnigent_client.tools import tool  # noqa: E402

from bankcore import casefile, scoring, store  # noqa: E402

MIN_NARRATIVE_CHARS = 900

# FinCEN expects a narrative that answers all five. A draft missing one
# of them wastes the reviewer's time and, filed as-is, is deficient.
REQUIRED_ELEMENTS = {
    "who": "the subject(s), by name, role, and relationship to the account",
    "what": "the instruments, amounts, and the conduct said to be suspicious",
    "when": "the date range of the activity",
    "where": "the accounts, branches, channels, and jurisdictions involved",
    "why": "why the activity is suspicious given this customer's known profile",
}

# Language that signals the narrative is arguing from vibes rather than
# evidence. A regulator reads these as an admission that the filer did
# not do the work.
HEDGE_PATTERNS = [
    r"\bmight be\b", r"\bcould possibly\b", r"\bseems shady\b", r"\bfeels\b",
    r"\bI think\b", r"\bprobably just\b", r"\bAI[- ]generated\b",
]


@tool
def submit_sar_draft(
    alert_id: str,
    suspicious_activity_type: str,
    narrative: str,
    subjects: list[str],
    activity_start_date: str,
    activity_end_date: str,
    total_suspicious_amount_usd: float,
    supporting_txn_ids: list[str],
    elements_covered: list[str],
) -> dict:
    """
    Submit a SAR narrative draft for human review. Does not file anything.

    The draft is validated against the elements a FinCEN narrative must
    contain, checked for hedging language, and checked to ensure the
    amount and transaction ids it claims actually exist in the ledger.
    It is then parked for a human reviewer.

    Write the narrative in plain chronological English, in the third
    person, citing amounts and dates exactly as the detectors reported
    them. Do not speculate about the subject's intent beyond what the
    transactions support, and do not quote adverse-media text verbatim.

    :param alert_id: Alert this draft relates to.
    :param suspicious_activity_type: e.g. ``structuring``,
        ``money laundering - trade based``, ``elder financial exploitation``.
    :param narrative: The full narrative text.
    :param subjects: Named subjects of the report.
    :param activity_start_date: ISO date of the earliest cited activity.
    :param activity_end_date: ISO date of the latest cited activity.
    :param total_suspicious_amount_usd: Aggregate amount reported.
    :param supporting_txn_ids: Ledger entries the narrative relies on.
    :param elements_covered: Which of who/what/when/where/why the
        narrative addresses.
    :returns: Acceptance or a list of deficiencies to fix.
    """
    alert = store.get_alert(alert_id)
    if not alert:
        return {"error": f"Unknown alert_id {alert_id!r}"}

    deficiencies: list[str] = []

    if len(narrative.strip()) < MIN_NARRATIVE_CHARS:
        deficiencies.append(
            f"Narrative is {len(narrative.strip())} characters; a filable narrative "
            f"needs at least {MIN_NARRATIVE_CHARS} to cover all five elements."
        )

    missing = [e for e in REQUIRED_ELEMENTS if e not in {x.lower() for x in elements_covered}]
    if missing:
        deficiencies.append(
            "Narrative does not claim to cover: "
            + ", ".join(f"{e} ({REQUIRED_ELEMENTS[e]})" for e in missing)
        )

    hedges = [p for p in HEDGE_PATTERNS if re.search(p, narrative, re.IGNORECASE)]
    if hedges:
        deficiencies.append(
            "Narrative contains hedging or speculative language "
            f"({', '.join(h.strip(chr(92) + 'b') for h in hedges)}). State what the "
            "records show; where an inference is required, name the evidence it rests on."
        )

    if not subjects:
        deficiencies.append("At least one named subject is required.")

    known = {t["txn_id"]: t for t in store.txns_for(alert["customer_id"])}
    unknown = [t for t in supporting_txn_ids if t not in known]
    if unknown:
        deficiencies.append(f"Cited transaction ids do not exist on this customer: {unknown}")
    if not supporting_txn_ids:
        deficiencies.append("A narrative must cite the transactions it is built from.")

    cited_total = sum(known[t]["amount"] for t in supporting_txn_ids if t in known)
    if cited_total and abs(cited_total - total_suspicious_amount_usd) / cited_total > 0.10:
        deficiencies.append(
            f"Reported amount ${total_suspicious_amount_usd:,.2f} differs from the sum of "
            f"the cited transactions (${cited_total:,.2f}) by more than 10%. Reconcile "
            f"the figure or cite the transactions that account for it."
        )

    if deficiencies:
        return {
            "accepted": False,
            "deficiencies": deficiencies,
            "note": "Draft rejected before review. Fix the deficiencies and resubmit.",
        }

    scorecard = scoring.score_alert(alert_id)
    case = casefile.read_case(alert_id) or {"alert_id": alert_id}
    case["sar_draft"] = {
        "status": "pending_human_review",
        "suspicious_activity_type": suspicious_activity_type,
        "subjects": subjects,
        "activity_start_date": activity_start_date,
        "activity_end_date": activity_end_date,
        "total_suspicious_amount_usd": round(total_suspicious_amount_usd, 2),
        "cited_transaction_total_usd": round(cited_total, 2),
        "supporting_txn_ids": supporting_txn_ids,
        "elements_covered": elements_covered,
        "narrative": narrative.strip(),
        "scorecard_score": scorecard["score"],
        "prepared_by": "AI agent (Argus AML triage)",
        "reviewed_by": None,
        "filed": False,
    }
    case.setdefault("customer_id", alert["customer_id"])
    case["requires_human_review"] = True
    case["human_review_status"] = "pending"
    path = casefile.write_case(alert_id, case)

    receipt = casefile.append(
        "sar_draft_submitted_for_review",
        {
            "alert_id": alert_id,
            "customer_id": alert["customer_id"],
            "suspicious_activity_type": suspicious_activity_type,
            "subjects": subjects,
            "total_suspicious_amount_usd": round(total_suspicious_amount_usd, 2),
            "narrative_chars": len(narrative.strip()),
            "supporting_txn_count": len(supporting_txn_ids),
            "filed": False,
        },
    )
    return {
        "accepted": True,
        "status": "pending_human_review",
        "filed": False,
        "case_file": str(path),
        "audit_entry_hash": receipt["entry_hash"],
        "note": (
            "Draft parked for human review. This tool cannot file a SAR: the filing "
            "decision and the submission to the financial intelligence unit remain "
            "with a qualified human in the bank's own reporting system."
        ),
    }
