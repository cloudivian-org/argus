"""Record the triage disposition for an alert into the case file."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omnigent_client.tools import tool  # noqa: E402

from bankcore import casefile, scoring, store  # noqa: E402

MIN_RATIONALE_CHARS = 220


@tool
def record_disposition(
    alert_id: str,
    disposition: str,
    rationale: str,
    key_evidence_txn_ids: list[str],
    typologies_considered: list[str],
    departure_from_scorecard_reason: str | None = None,
) -> dict:
    """
    Record the investigator's disposition for an alert.

    This writes the working case file and appends a hash-chained entry to
    the audit ledger. It is the moment the reasoning becomes the bank's
    permanent record, so the rationale must stand on its own two years
    from now to a reader who has never seen this conversation.

    A disposition that departs from the scorecard's banded
    recommendation is permitted but must carry an explicit reason.

    :param alert_id: Alert being dispositioned.
    :param disposition: One of ``close_no_sar``, ``close_with_edd``,
        ``escalate_l2``, ``recommend_sar``.
    :param rationale: Written reasoning citing specific evidence.
        Must address why the activity is, or is not, suspicious.
    :param key_evidence_txn_ids: The exact ledger entries relied upon.
    :param typologies_considered: Typologies assessed, including the
        ones ruled out — a triage that only lists what it found is not
        a triage.
    :param departure_from_scorecard_reason: Required when the
        disposition differs from the scorecard recommendation.
    :returns: The stored case file with its ledger receipt.
    """
    alert = store.get_alert(alert_id)
    if not alert:
        return {"error": f"Unknown alert_id {alert_id!r}"}

    if disposition not in casefile.VALID_DISPOSITIONS:
        return {
            "error": f"Invalid disposition {disposition!r}",
            "valid_dispositions": sorted(casefile.VALID_DISPOSITIONS),
        }

    if len(rationale.strip()) < MIN_RATIONALE_CHARS:
        return {
            "error": (
                f"Rationale is {len(rationale.strip())} characters; the case-file "
                f"standard requires at least {MIN_RATIONALE_CHARS}. State what the "
                f"activity was, why it is or is not consistent with the customer's "
                f"KYC profile, and what evidence settles the question."
            ),
            "rejected": True,
        }

    if not key_evidence_txn_ids:
        return {
            "error": (
                "A disposition must cite the transactions it relies on. Pass the "
                "transaction ids returned by the typology detectors."
            ),
            "rejected": True,
        }

    scorecard = scoring.score_alert(alert_id)
    recommended = scorecard["recommended_disposition"]
    departs = disposition != recommended
    if departs and not departure_from_scorecard_reason:
        return {
            "error": (
                f"Disposition {disposition!r} departs from the scorecard "
                f"recommendation {recommended!r} (score {scorecard['score']}, band "
                f"{scorecard['band']}). Supply departure_from_scorecard_reason "
                f"explaining why the scorecard is wrong on this alert."
            ),
            "rejected": True,
            "scorecard_recommendation": recommended,
            "scorecard_score": scorecard["score"],
        }

    known_txns = {t["txn_id"] for t in store.txns_for(alert["customer_id"])}
    unknown = [t for t in key_evidence_txn_ids if t not in known_txns]
    if unknown:
        return {
            "error": (
                "These transaction ids do not exist on this customer's accounts: "
                f"{unknown}. Every cited id must come from tool output."
            ),
            "rejected": True,
        }

    document = {
        "alert_id": alert_id,
        "customer_id": alert["customer_id"],
        "detection_rule": alert["detection_rule"],
        "disposition": disposition,
        "rationale": rationale.strip(),
        "typologies_considered": typologies_considered,
        "key_evidence_txn_ids": key_evidence_txn_ids,
        "scorecard": {
            "score": scorecard["score"],
            "band": scorecard["band"],
            "recommended_disposition": recommended,
            "factors": scorecard["factors"],
        },
        "departed_from_scorecard": departs,
        "departure_reason": departure_from_scorecard_reason,
        "sar_draft": (casefile.read_case(alert_id) or {}).get("sar_draft"),
        "prepared_by": "AI agent (Argus AML triage)",
        "requires_human_review": True,
        "human_review_status": "pending",
    }
    path = casefile.write_case(alert_id, document)
    receipt = casefile.append(
        "disposition_recorded",
        {
            "alert_id": alert_id,
            "customer_id": alert["customer_id"],
            "disposition": disposition,
            "scorecard_score": scorecard["score"],
            "departed_from_scorecard": departs,
            "evidence_txn_count": len(key_evidence_txn_ids),
        },
    )
    return {
        "summary": (
            f"DISPOSITION RECORDED (pending human review) — {alert_id} → {disposition}\n"
            f"Scorecard: {scorecard['score']}/100 ({scorecard['band']}), recommended "
            f"{recommended}"
            + (
                f"\nDEPARTED from the scorecard. Reason given: "
                f"{departure_from_scorecard_reason}"
                if departs else " — disposition agrees with the scorecard."
            )
            + f"\nEvidence cited: {len(key_evidence_txn_ids)} transaction(s). "
            f"Typologies considered: {', '.join(typologies_considered)}.\n"
            f"Case file: {path}\n"
            f"Audit ledger entry: {receipt['entry_hash'][:16]}…\n"
            "This is a RECOMMENDATION ONLY. No alert has been closed and no report "
            "has been filed — a qualified human does that in the bank's own system."
        ),
        "recorded": True,
        "case_file": str(path),
        "disposition": disposition,
        "scorecard_score": scorecard["score"],
        "scorecard_recommendation": recommended,
        "departed_from_scorecard": departs,
        "audit_entry_hash": receipt["entry_hash"],
        "human_review_status": "pending",
        "note": (
            "Recorded as a recommendation only. No alert is closed and no report is "
            "filed until a qualified human reviewer signs it off in the bank's own "
            "case-management system."
        ),
    }
