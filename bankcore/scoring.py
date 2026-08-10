"""Deterministic risk scorecard for an AML alert.

The scorecard exists so the *decision* is auditable and reproducible,
not a model's mood. Weights are explicit, every contribution is itemised
with the evidence that produced it, and a human or a model-risk
validator can recompute the total by hand.

The agent may argue with the score in its narrative — that is the point
of having an analyst — but it must state the score, and any departure
from the banded recommendation has to be justified in writing.
"""

from __future__ import annotations

from . import screening, store, typologies

# Weight per triggered typology, scaled by detector confidence.
TYPOLOGY_WEIGHTS = {
    "structuring": 30,
    "pass_through": 28,
    "rapid_in_out": 26,
    "round_value_wires": 22,
    "behaviour_break": 22,
    "jurisdiction_exposure": 16,
    "profile_deviation": 14,
    "counterparty_concentration": 8,
}

CONFIDENCE_SCALE = {"high": 1.0, "medium": 0.65, "low": 0.35, "n/a": 0.0}

# Static customer-risk contributions.
KYC_RISK_POINTS = {"high": 12, "medium": 6, "low": 0}

# Per-category ceilings. Without these a single category (typically
# screening, where one counterparty can produce several list matches)
# saturates the total and destroys the scorecard's ability to rank one
# alert against another — the property the whole queue depends on.
CATEGORY_CAPS = {"typology": 60, "screening": 25, "customer": 15, "history": 10}

# Typologies that measure "this looks unusual for the customer". When the
# unusual movement is settled against a regulated, purpose-identifying
# counterparty, the unusualness is explained and these lose most of their
# weight. Predicate typologies (structuring, pass-through, layering) are
# never discounted: a title company in the ledger does not explain
# fourteen sub-threshold cash deposits.
BEHAVIOURAL_TYPOLOGIES = {
    "profile_deviation",
    "behaviour_break",
    "counterparty_concentration",
}
EXPLAINED_DISCOUNT = 0.15

BANDS = [
    (80, "critical", "recommend_sar", "Recommend a SAR filing and apply enhanced monitoring."),
    (60, "high", "escalate_l2", "Escalate to a Level 2 investigator for a SAR decision."),
    (35, "medium", "close_with_edd", "Close the alert but apply enhanced due diligence and re-review."),
    (0, "low", "close_no_sar", "Close the alert with a documented rationale."),
]


def score_alert(alert_id: str, lookback_days: int | None = None) -> dict:
    """
    Compute the deterministic risk score for one alert.

    :param alert_id: Alert to score.
    :param lookback_days: Override the alert's own lookback window.
    :returns: A scorecard with the total, band, recommendation, and an
        itemised list of every contributing factor.
    :raises ValueError: If the alert is unknown.
    """
    alert = store.get_alert(alert_id)
    if not alert:
        raise ValueError(f"Unknown alert_id: {alert_id}")
    customer_id = alert["customer_id"]
    customer = store.get_customer(customer_id) or {}
    window = lookback_days or alert.get("lookback_days", 90)

    factors: list[dict] = []

    # 1. Behavioural typologies.
    explained = _explained_activity(customer_id, window)
    findings = typologies.run_all(customer_id, window)
    for f in findings:
        if not f["triggered"]:
            continue
        weight = TYPOLOGY_WEIGHTS.get(f["typology"], 10)
        points = round(weight * CONFIDENCE_SCALE.get(f["confidence"], 0.35), 1)
        basis = f["summary"]
        discounted = (
            explained["applies"] and f["typology"] in BEHAVIOURAL_TYPOLOGIES
        )
        if discounted:
            points = round(points * EXPLAINED_DISCOUNT, 1)
            basis += (
                f" DISCOUNTED to {EXPLAINED_DISCOUNT:.0%}: "
                f"{explained['share_pct']:.0f}% of value in this window settles against "
                f"regulated, purpose-identifying counterparties "
                f"({explained['examples']}), which explains the deviation."
            )
        factors.append(
            {
                "category": "typology",
                "factor": f["typology"],
                "points": points,
                "max_points": weight,
                "basis": basis,
                "explained_discount_applied": discounted,
                "evidence_txn_count": len(f["evidence_txn_ids"]),
            }
        )

    # 2. Screening: the customer, and every counterparty they touched.
    screened = _screen_network(customer_id, customer, window)
    for hit in screened["strong_hits"]:
        points = 35 if hit["scope"] == "counterparty" else 40
        factors.append(
            {
                "category": "screening",
                "factor": f"sanctions_or_pep_match:{hit['matched_entry']}",
                "points": points,
                "max_points": 40,
                "basis": (
                    f"{hit['scope'].title()} \"{hit['name']}\" matches {hit['list_name']} "
                    f"entry \"{hit['matched_entry']}\" at {hit['adjusted_score']:.2f} "
                    f"(programs: {', '.join(hit['programs']) or 'n/a'})."
                ),
                "evidence_txn_count": 0,
            }
        )
    for hit in screened["possible_hits"]:
        factors.append(
            {
                "category": "screening",
                "factor": f"possible_list_match:{hit['matched_entry']}",
                "points": 10,
                "max_points": 40,
                "basis": (
                    f"{hit['scope'].title()} \"{hit['name']}\" is a possible match to "
                    f"{hit['list_name']} entry \"{hit['matched_entry']}\" "
                    f"({hit['adjusted_score']:.2f}) — requires analyst disposition."
                ),
                "evidence_txn_count": 0,
            }
        )

    # 3. Static customer risk.
    kyc_band = customer.get("kyc_risk_rating", "low")
    if KYC_RISK_POINTS.get(kyc_band):
        factors.append(
            {
                "category": "customer",
                "factor": "kyc_risk_rating",
                "points": KYC_RISK_POINTS[kyc_band],
                "max_points": KYC_RISK_POINTS["high"],
                "basis": f"Customer carries a {kyc_band} KYC risk rating.",
                "evidence_txn_count": 0,
            }
        )
    if customer.get("pep_status") or any(
        o.get("pep") for o in customer.get("beneficial_owners", [])
    ):
        factors.append(
            {
                "category": "customer",
                "factor": "pep_exposure",
                "points": 12,
                "max_points": 12,
                "basis": "Customer is, or is controlled by, a politically exposed person.",
                "evidence_txn_count": 0,
            }
        )
    if customer.get("vulnerable_customer_flag"):
        factors.append(
            {
                "category": "customer",
                "factor": "vulnerable_customer",
                "points": 8,
                "max_points": 8,
                "basis": (
                    "Customer is flagged as vulnerable — raises the duty of care and "
                    "changes the likely SAR classification toward victim exploitation."
                ),
                "evidence_txn_count": 0,
            }
        )

    # 4. Investigation history — a repeat pattern is materially worse.
    history = [c for c in store.prior_cases() if c["customer_id"] == customer_id]
    repeats = [c for c in history if c["detection_rule"] == alert["detection_rule"]]
    if repeats:
        factors.append(
            {
                "category": "history",
                "factor": "repeat_alert_same_rule",
                "points": 14,
                "max_points": 14,
                "basis": (
                    f"Rule {alert['detection_rule']} has fired before for this customer "
                    f"({', '.join(c['case_id'] for c in repeats)}), previously disposed as "
                    f"{', '.join(c['disposition'] for c in repeats)}."
                    + (
                        " Committed follow-up action was never completed."
                        if any(c.get("follow_up") for c in repeats) else ""
                    )
                ),
                "evidence_txn_count": 0,
            }
        )

    # 5. Mitigants — the scorecard must be able to argue the alert down.
    mitigants = _mitigants(customer, customer_id, window)
    factors.extend(mitigants)

    raw_total, capped = _apply_caps(factors)
    total = max(0, min(100, round(raw_total)))
    band, band_name, recommendation, guidance = _band(total)

    ranked = sorted(factors, key=lambda f: f["points"], reverse=True)
    ledger = "\n".join(
        f"  {f['points']:>+7.1f}  {f['category']:<9} {f['factor']}\n"
        f"           {f['basis']}"
        for f in ranked
    )
    caps_note = (
        "\n".join(
            f"  {cat} capped: {v['uncapped']} → {v['capped_to']}"
            for cat, v in capped.items()
        )
        if capped else ""
    )

    return {
        "summary": (
            f"RISK SCORE {total}/100 — {band_name.upper()} — "
            f"scorecard recommends: {recommendation}\n"
            f"{guidance}\n\n"
            f"Scoring ledger (weights fixed in code; recomputable by hand):\n{ledger}\n"
            + (f"\nCategory ceilings applied:\n{caps_note}\n" if caps_note else "")
            + f"\nTotal after ceilings: {round(raw_total, 1)} → clamped to {total}/100.\n"
            f"The recommendation is ADVISORY. Departing from it is allowed, but "
            f"record_disposition will refuse the write until you supply a written reason."
        ),
        "alert_id": alert_id,
        "customer_id": customer_id,
        "lookback_days": window,
        "uncapped_total": round(sum(f["points"] for f in factors), 1),
        "raw_total": round(raw_total, 1),
        "category_caps_applied": capped,
        "score": total,
        "band": band_name,
        "band_floor": band,
        "recommended_disposition": recommendation,
        "recommendation_guidance": guidance,
        "factors": sorted(factors, key=lambda f: f["points"], reverse=True),
        "triggered_typologies": [f["typology"] for f in findings if f["triggered"]],
        "screening_summary": {
            "strong_hits": len(screened["strong_hits"]),
            "possible_hits": len(screened["possible_hits"]),
            "names_screened": screened["names_screened"],
        },
        "methodology": (
            "score = sum(typology_weight x confidence_scale, behavioural typologies "
            "discounted where activity is independently explained) + screening + static "
            "customer risk + history - mitigants; each category capped at "
            f"{CATEGORY_CAPS}, then clamped to 0-100. Weights are fixed in "
            "bankcore/scoring.py and are reproducible by hand from the factor list."
        ),
        "override_rule": (
            "The banded recommendation is advisory. An investigator may depart from it, "
            "but the departure and its reasoning must be recorded in the disposition."
        ),
    }


def _screen_network(customer_id: str, customer: dict, window: int) -> dict:
    """Screen the customer, its beneficial owners, and its counterparties."""
    names: list[tuple[str, str, str | None]] = []
    names.append((customer.get("legal_name", customer_id), "customer",
                  customer.get("residence_country") or customer.get("incorporation_country")))
    for owner in customer.get("beneficial_owners", []):
        names.append((owner["name"], "beneficial_owner", owner.get("country")))
    seen: set[str] = set()
    for t in store.txns_for(customer_id, lookback_days=window):
        key = t["counterparty_name"]
        if key in seen or key in ("CASH DEPOSIT", "ATM WITHDRAWAL"):
            continue
        seen.add(key)
        names.append((key, "counterparty", t["counterparty_country"]))

    strong, possible = [], []
    for name, scope, country in names:
        result = screening.screen_name(name, country)
        for match in result["matches"]:
            row = {**match, "name": name, "scope": scope}
            (strong if match["classification"] == "strong_match" else possible).append(row)
    return {"strong_hits": strong, "possible_hits": possible, "names_screened": len(names)}


# Counterparty types that identify a transaction's purpose on their own.
# A title company, an escrow agent, or a payroll processor is itself a
# regulated entity that already performed its own diligence.
EXPLANATORY_COUNTERPARTIES = (
    "TITLE COMPANY", "ESCROW", "MORTGAGE", "PAYROLL", "SOCIAL SECURITY", "PENSION",
)


def _explained_activity(customer_id: str, window: int) -> dict:
    """
    Measure how much of the window's value is independently explained.

    :returns: Share of value settled against purpose-identifying
        regulated counterparties, and whether that share is large
        enough to discount the behavioural typologies.
    """
    txns = store.txns_for(customer_id, lookback_days=window)
    total = sum(t["amount"] for t in txns)
    explained = [
        t for t in txns
        if any(token in t["counterparty_name"].upper() for token in EXPLANATORY_COUNTERPARTIES)
    ]
    explained_value = sum(t["amount"] for t in explained)
    share = explained_value / total if total else 0.0
    top = sorted(explained, key=lambda t: t["amount"], reverse=True)[:3]
    return {
        "applies": share >= 0.5,
        "share_pct": share * 100,
        "explained_value_usd": round(explained_value, 2),
        "total_value_usd": round(total, 2),
        "examples": "; ".join(f"{t['counterparty_name']} ${t['amount']:,.0f}" for t in top)
        or "none",
    }


def _apply_caps(factors: list[dict]) -> tuple[float, dict]:
    """
    Sum the factors with per-category ceilings applied.

    :returns: The capped total, and a report of which categories were
        capped and by how much — surfaced in the scorecard so a
        validator can see the ceiling bind rather than guess.
    """
    by_category: dict[str, float] = {}
    for f in factors:
        by_category.setdefault(f["category"], 0.0)
        by_category[f["category"]] += f["points"]

    total = 0.0
    capped: dict[str, dict] = {}
    for category, subtotal in by_category.items():
        ceiling = CATEGORY_CAPS.get(category)
        if ceiling is not None and subtotal > ceiling:
            capped[category] = {"uncapped": round(subtotal, 1), "capped_to": ceiling}
            subtotal = float(ceiling)
        total += subtotal
    return total, capped


def _mitigants(customer: dict, customer_id: str, window: int) -> list[dict]:
    """Return negative-point factors that argue the alert down."""
    out: list[dict] = []

    # A low risk rating only mitigates while the review behind it is
    # current. Age it against the as-of date rather than a fixed cutoff,
    # so this factor agrees with the staleness flag `get_customer_profile`
    # reports instead of contradicting it.
    last_review = customer.get("last_kyc_review")
    review_age = store.days_ago(last_review) if last_review else None
    if customer.get("kyc_risk_rating") == "low" and review_age is not None and review_age <= 365:
        out.append(
            {
                "category": "mitigant",
                "factor": "current_kyc_and_low_risk_rating",
                "points": -6,
                "max_points": -6,
                "basis": (
                    f"Low KYC risk rating with a review completed {last_review} "
                    f"({review_age} days ago) — the customer profile is current."
                ),
                "evidence_txn_count": 0,
            }
        )

    tenure = customer.get("onboarded", "")
    if tenure and tenure < "2018-01-01":
        out.append(
            {
                "category": "mitigant",
                "factor": "long_tenure",
                "points": -4,
                "max_points": -4,
                "basis": f"Relationship established {tenure}; long observed history.",
                "evidence_txn_count": 0,
            }
        )
    return out


def _band(total: int) -> tuple[int, str, str, str]:
    """Map a score onto its band, disposition recommendation, and guidance."""
    for floor, name, recommendation, guidance in BANDS:
        if total >= floor:
            return floor, name, recommendation, guidance
    return 0, "low", "close_no_sar", BANDS[-1][3]
