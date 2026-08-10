"""Deterministic AML typology detectors.

These functions do the counting. The agent reads their output and
reasons about it, but never produces the numbers itself — every figure
that reaches a SAR narrative can be traced back to a detector here and
recomputed by a human or a model validator.

Each detector returns a uniform finding dict::

    {
      "typology": "structuring",
      "triggered": true,
      "confidence": "high",            # high | medium | low
      "summary": "one-line plain-English statement",
      "metrics": {...},                # the raw numbers
      "evidence_txn_ids": [...],       # the exact ledger entries
      "regulatory_reference": "..."    # what rule this maps to
    }
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from . import store

CTR_THRESHOLD_USD = 10_000.0


def _finding(
    typology: str,
    triggered: bool,
    summary: str,
    *,
    confidence: str = "low",
    metrics: dict | None = None,
    txn_ids: list[str] | None = None,
    reference: str = "",
) -> dict:
    """Build a uniform detector finding."""
    return {
        "typology": typology,
        "triggered": triggered,
        "confidence": confidence if triggered else "n/a",
        "summary": summary,
        "metrics": metrics or {},
        "evidence_txn_ids": (txn_ids or [])[:60],
        "regulatory_reference": reference,
    }


# ── detectors ────────────────────────────────────────────────────────


def structuring(customer_id: str, lookback_days: int = 90) -> dict:
    """Detect cash deposits clustered just below the CTR threshold."""
    txns = store.txns_for(customer_id, lookback_days=lookback_days, direction="credit")
    near = [
        t for t in txns
        if t.get("is_cash") and CTR_THRESHOLD_USD * 0.75 <= t["amount"] < CTR_THRESHOLD_USD
    ]
    over = [t for t in txns if t.get("is_cash") and t["amount"] >= CTR_THRESHOLD_USD]
    branches = {t.get("branch_code") for t in near if t.get("branch_code")}
    total = sum(t["amount"] for t in near)

    if len(near) < 3:
        return _finding("structuring", False, "No cluster of below-threshold cash deposits.")

    span = _day_span(near)
    return _finding(
        "structuring",
        True,
        f"{len(near)} cash deposits between ${CTR_THRESHOLD_USD * 0.75:,.0f} and "
        f"${CTR_THRESHOLD_USD:,.0f} totalling ${total:,.2f} over {span} days across "
        f"{len(branches)} branches, with {len(over)} deposit(s) at or above the "
        f"${CTR_THRESHOLD_USD:,.0f} reporting threshold.",
        confidence="high" if len(near) >= 6 and len(branches) >= 2 and not over else "medium",
        metrics={
            "below_threshold_deposit_count": len(near),
            "at_or_above_threshold_deposit_count": len(over),
            "total_below_threshold_usd": round(total, 2),
            "distinct_branches": sorted(b for b in branches),
            "day_span": span,
            "mean_deposit_usd": round(total / len(near), 2),
            "max_deposit_usd": round(max(t["amount"] for t in near), 2),
        },
        txn_ids=[t["txn_id"] for t in near],
        reference="31 CFR 1010.313 (CTR) / 31 USC 5324 (structuring); FATF R.10, R.20",
    )


def pass_through(customer_id: str, lookback_days: int = 90) -> dict:
    """Detect funnel / mule behaviour: many small credits, near-total outflow."""
    txns = store.txns_for(customer_id, lookback_days=lookback_days)
    credits = [t for t in txns if t["direction"] == "credit"]
    debits = [t for t in txns if t["direction"] == "debit"]
    if not credits:
        return _finding("pass_through", False, "No inbound activity in the window.")

    in_total = sum(t["amount"] for t in credits)
    out_total = sum(t["amount"] for t in debits)
    ratio = out_total / in_total if in_total else 0.0
    senders = {t["counterparty_name"] for t in credits if t["channel"] in ("p2p", "wire", "ach")}
    cash_out = sum(t["amount"] for t in debits if t.get("is_cash") or t["channel"] == "atm")
    crypto_out = sum(t["amount"] for t in debits if t["channel"] == "crypto_exchange")

    triggered = ratio >= 0.80 and len(senders) >= 10
    if not triggered:
        return _finding(
            "pass_through",
            False,
            f"Pass-through ratio {ratio:.2f} across {len(senders)} distinct senders "
            f"— below the funnel-account threshold.",
        )

    return _finding(
        "pass_through",
        True,
        f"{len(credits)} inbound credits totalling ${in_total:,.2f} from {len(senders)} "
        f"unrelated senders, with {ratio * 100:.0f}% forwarded out — "
        f"${cash_out:,.2f} as ATM cash and ${crypto_out:,.2f} to a virtual-asset venue.",
        confidence="high" if ratio >= 0.9 and len(senders) >= 20 else "medium",
        metrics={
            "inbound_count": len(credits),
            "inbound_total_usd": round(in_total, 2),
            "outbound_total_usd": round(out_total, 2),
            "pass_through_ratio": round(ratio, 3),
            "distinct_senders": len(senders),
            "atm_cash_out_usd": round(cash_out, 2),
            "virtual_asset_out_usd": round(crypto_out, 2),
            "mean_inbound_usd": round(in_total / len(credits), 2),
        },
        txn_ids=[t["txn_id"] for t in credits + debits],
        reference="FinCEN money-mule advisory FIN-2020-A008; FATF R.10, R.15",
    )


def round_value_wires(customer_id: str, lookback_days: int = 90) -> dict:
    """Detect repeated round-dollar cross-border wires — an invoicing red flag."""
    txns = store.txns_for(customer_id, lookback_days=lookback_days, direction="debit")
    wires = [
        t for t in txns
        if t["channel"] == "wire"
        and t["counterparty_country"] != "US"
        and t["amount"] >= 50_000
        and t["amount"] % 10_000 == 0
    ]
    if len(wires) < 3:
        return _finding("round_value_wires", False, "No repeated round-value cross-border wires.")

    total = sum(t["amount"] for t in wires)
    by_cp: dict[str, float] = defaultdict(float)
    for t in wires:
        by_cp[t["counterparty_name"]] += t["amount"]

    return _finding(
        "round_value_wires",
        True,
        f"{len(wires)} exactly round-value wires totalling ${total:,.2f} to "
        f"{len(by_cp)} cross-border counterparties — commercially implausible for "
        f"invoice settlement, where amounts carry cents and freight adjustments.",
        confidence="high" if len(wires) >= 5 else "medium",
        metrics={
            "wire_count": len(wires),
            "total_usd": round(total, 2),
            "counterparty_totals_usd": {k: round(v, 2) for k, v in sorted(by_cp.items())},
            "distinct_amounts": sorted({t["amount"] for t in wires}),
        },
        txn_ids=[t["txn_id"] for t in wires],
        reference="FATF Trade-Based Money Laundering (2020); FinCEN advisory FIN-2010-A001",
    )


def jurisdiction_exposure(customer_id: str, lookback_days: int = 90) -> dict:
    """Quantify value flowing to and from high-risk jurisdictions."""
    txns = store.txns_for(customer_id, lookback_days=lookback_days)
    by_country: dict[str, dict] = defaultdict(lambda: {"in_usd": 0.0, "out_usd": 0.0, "count": 0})
    for t in txns:
        cc = t["counterparty_country"]
        entry = by_country[cc]
        entry["count"] += 1
        entry["in_usd" if t["direction"] == "credit" else "out_usd"] += t["amount"]

    high = {
        cc: v for cc, v in by_country.items()
        if store.country_risk(cc) == "high"
    }
    if not high:
        return _finding("jurisdiction_exposure", False, "No exposure to high-risk jurisdictions.")

    detail = {
        cc: {
            "country": store.jurisdictions().get(cc, {}).get("name", cc),
            "risk_note": store.jurisdictions().get(cc, {}).get("note", ""),
            "in_usd": round(v["in_usd"], 2),
            "out_usd": round(v["out_usd"], 2),
            "txn_count": v["count"],
        }
        for cc, v in sorted(high.items())
    }
    total = sum(v["in_usd"] + v["out_usd"] for v in high.values())
    customer = store.get_customer(customer_id) or {}
    declared = set(customer.get("declared_trade_corridors") or [])
    undeclared = sorted(set(high) - declared) if declared else sorted(high)

    return _finding(
        "jurisdiction_exposure",
        True,
        f"${total:,.2f} moved across {len(high)} high-risk jurisdiction(s): "
        f"{', '.join(sorted(high))}."
        + (
            f" {', '.join(undeclared)} sit outside the customer's declared corridors "
            f"({', '.join(sorted(declared))})."
            if declared and undeclared else ""
        ),
        confidence="high" if undeclared else "medium",
        metrics={
            "high_risk_total_usd": round(total, 2),
            "by_country": detail,
            "declared_corridors": sorted(declared),
            "undeclared_high_risk_corridors": undeclared,
        },
        txn_ids=[t["txn_id"] for t in txns if t["counterparty_country"] in high],
        reference="FATF R.19 (higher-risk countries); 31 CFR 1010.610 (correspondent EDD)",
    )


def rapid_in_out(customer_id: str, lookback_days: int = 120) -> dict:
    """Detect layering: value received and forwarded within 48 hours."""
    txns = store.txns_for(customer_id, lookback_days=lookback_days)
    credits = sorted(
        (t for t in txns if t["direction"] == "credit" and t["amount"] >= 50_000),
        key=lambda t: t["booking_date"],
    )
    debits = sorted(
        (t for t in txns if t["direction"] == "debit" and t["amount"] >= 50_000),
        key=lambda t: t["booking_date"],
    )
    pairs = []
    used: set[str] = set()
    for c in credits:
        c_day = store._as_date(c["booking_date"])
        for dbt in debits:
            if dbt["txn_id"] in used:
                continue
            gap = (store._as_date(dbt["booking_date"]) - c_day).days
            if 0 <= gap <= 2 and abs(dbt["amount"] - c["amount"]) / c["amount"] <= 0.05:
                pairs.append(
                    {
                        "in_txn": c["txn_id"],
                        "out_txn": dbt["txn_id"],
                        "in_usd": c["amount"],
                        "out_usd": dbt["amount"],
                        "retained_usd": round(c["amount"] - dbt["amount"], 2),
                        "hours_held_max": gap * 24,
                        "from": c["counterparty_name"],
                        "to": dbt["counterparty_name"],
                    }
                )
                used.add(dbt["txn_id"])
                break

    if len(pairs) < 3:
        return _finding("rapid_in_out", False, "No repeated in-and-out layering pattern.")

    onward = {p["to"] for p in pairs}
    total_in = sum(p["in_usd"] for p in pairs)
    retained = sum(p["retained_usd"] for p in pairs)
    return _finding(
        "rapid_in_out",
        True,
        f"{len(pairs)} matched in/out pairs: ${total_in:,.2f} received and "
        f"{(1 - retained / total_in) * 100:.1f}% forwarded within 48 hours to "
        f"{len(onward)} related entities, retaining only ${retained:,.2f} "
        f"({retained / total_in * 100:.1f}%) — inconsistent with a genuine "
        f"commercial margin.",
        confidence="high" if len(pairs) >= 4 else "medium",
        metrics={
            "matched_pairs": len(pairs),
            "total_received_usd": round(total_in, 2),
            "total_retained_usd": round(retained, 2),
            "retained_pct": round(retained / total_in * 100, 2),
            "onward_counterparties": sorted(onward),
            "pairs": pairs,
        },
        txn_ids=[p["in_txn"] for p in pairs] + [p["out_txn"] for p in pairs],
        reference="FATF R.10/R.12 (layering, PEP); Wolfsberg Correspondent Banking Principles",
    )


def profile_deviation(customer_id: str, lookback_days: int = 90) -> dict:
    """Compare observed turnover against the KYC-declared expectation."""
    customer = store.get_customer(customer_id)
    if not customer:
        return _finding("profile_deviation", False, "Customer not found.")

    txns = store.txns_for(customer_id, lookback_days=lookback_days)
    months = max(lookback_days / 30.0, 1.0)
    obs_credit = sum(t["amount"] for t in txns if t["direction"] == "credit") / months
    obs_debit = sum(t["amount"] for t in txns if t["direction"] == "debit") / months
    exp_credit = float(customer.get("expected_monthly_credit_usd", 0)) or 1.0
    exp_debit = float(customer.get("expected_monthly_debit_usd", 0)) or 1.0
    c_mult = obs_credit / exp_credit
    d_mult = obs_debit / exp_debit
    worst = max(c_mult, d_mult)

    if worst < 2.0:
        return _finding(
            "profile_deviation",
            False,
            f"Turnover within expectation (credits {c_mult:.1f}x, debits {d_mult:.1f}x declared).",
        )

    return _finding(
        "profile_deviation",
        True,
        f"Observed monthly turnover runs {c_mult:.1f}x declared credits and "
        f"{d_mult:.1f}x declared debits. Declared source of funds: "
        f"\"{customer.get('source_of_funds', 'not recorded')}\".",
        confidence="high" if worst >= 4 else "medium",
        metrics={
            "observed_monthly_credit_usd": round(obs_credit, 2),
            "expected_monthly_credit_usd": exp_credit,
            "credit_multiple": round(c_mult, 2),
            "observed_monthly_debit_usd": round(obs_debit, 2),
            "expected_monthly_debit_usd": exp_debit,
            "debit_multiple": round(d_mult, 2),
            "declared_source_of_funds": customer.get("source_of_funds"),
            "last_kyc_review": customer.get("last_kyc_review"),
        },
        txn_ids=[t["txn_id"] for t in txns if t["amount"] >= exp_credit],
        reference="FATF R.10 (ongoing CDD); 31 CFR 1020.210(a)(2)(v) (customer risk profile)",
    )


def behaviour_break(customer_id: str, lookback_days: int = 90) -> dict:
    """Detect an abrupt break from a long-established activity baseline."""
    recent = store.txns_for(customer_id, lookback_days=lookback_days)
    everything = store.txns_for(customer_id)
    baseline = [t for t in everything if store.days_ago(t["booking_date"]) > lookback_days]
    if not baseline:
        return _finding("behaviour_break", False, "Insufficient history to establish a baseline.")

    def profile(rows: list[dict], days: int) -> dict:
        months = max(days / 30.0, 1.0)
        out = [t for t in rows if t["direction"] == "debit"]
        cross = [t for t in out if t["counterparty_country"] != "US"]
        return {
            "monthly_outflow_usd": sum(t["amount"] for t in out) / months,
            "cross_border_monthly_usd": sum(t["amount"] for t in cross) / months,
            "max_single_debit_usd": max((t["amount"] for t in out), default=0.0),
            "countries": sorted({t["counterparty_country"] for t in cross}),
        }

    base_days = max(
        (store.days_ago(t["booking_date"]) for t in baseline), default=lookback_days + 1
    ) - lookback_days
    b = profile(baseline, base_days)
    r = profile(recent, lookback_days)
    mult = r["monthly_outflow_usd"] / b["monthly_outflow_usd"] if b["monthly_outflow_usd"] else 99.0
    new_countries = sorted(set(r["countries"]) - set(b["countries"]))

    if mult < 2.5 and not new_countries:
        return _finding(
            "behaviour_break",
            False,
            f"Recent outflow is {mult:.1f}x the historical baseline with no new corridors.",
        )

    customer = store.get_customer(customer_id) or {}
    vuln = customer.get("vulnerable_customer_flag")
    return _finding(
        "behaviour_break",
        True,
        f"Monthly outflow rose to {mult:.1f}x the {base_days}-day historical baseline "
        f"(${b['monthly_outflow_usd']:,.0f} → ${r['monthly_outflow_usd']:,.0f})"
        + (f", with first-ever activity to {', '.join(new_countries)}" if new_countries else "")
        + (
            ". The customer carries a vulnerable-customer flag, so victim-based "
            "exploitation must be considered alongside wilful conduct."
            if vuln else "."
        ),
        confidence="high" if mult >= 5 or (new_countries and vuln) else "medium",
        metrics={
            "baseline_monthly_outflow_usd": round(b["monthly_outflow_usd"], 2),
            "recent_monthly_outflow_usd": round(r["monthly_outflow_usd"], 2),
            "outflow_multiple": round(mult, 2),
            "baseline_window_days": base_days,
            "new_corridors": new_countries,
            "max_single_debit_recent_usd": round(r["max_single_debit_usd"], 2),
            "vulnerable_customer_flag": bool(vuln),
            "customer_age_years": _age_years(customer.get("date_of_birth")),
        },
        txn_ids=[
            t["txn_id"] for t in recent
            if t["direction"] == "debit" and t["counterparty_country"] in new_countries
        ],
        reference="FinCEN elder-exploitation advisory FIN-2022-A002; FATF R.10",
    )


def counterparty_concentration(customer_id: str, lookback_days: int = 90) -> dict:
    """Flag outbound value concentrated in a handful of counterparties."""
    txns = store.txns_for(customer_id, lookback_days=lookback_days, direction="debit")
    if not txns:
        return _finding("counterparty_concentration", False, "No outbound activity.")
    by_cp: dict[str, float] = defaultdict(float)
    for t in txns:
        by_cp[t["counterparty_name"]] += t["amount"]
    total = sum(by_cp.values())
    top = sorted(by_cp.items(), key=lambda kv: kv[1], reverse=True)[:3]
    top_share = sum(v for _, v in top) / total if total else 0.0

    if top_share < 0.75 or len(by_cp) < 4 or len(by_cp) > 25:
        return _finding(
            "counterparty_concentration",
            False,
            f"Outbound value spread across {len(by_cp)} counterparties "
            f"(top 3 = {top_share * 100:.0f}%).",
        )
    return _finding(
        "counterparty_concentration",
        True,
        f"{top_share * 100:.0f}% of ${total:,.2f} outbound value went to just "
        f"{len(top)} counterparties: "
        + "; ".join(f"{k} (${v:,.0f})" for k, v in top)
        + ".",
        confidence="medium",
        metrics={
            "outbound_total_usd": round(total, 2),
            "distinct_counterparties": len(by_cp),
            "top_counterparties_usd": {k: round(v, 2) for k, v in top},
            "top3_share_pct": round(top_share * 100, 1),
        },
        txn_ids=[t["txn_id"] for t in txns if t["counterparty_name"] in dict(top)],
        reference="FATF R.10 (ongoing monitoring)",
    )


DETECTORS = {
    "structuring": structuring,
    "pass_through": pass_through,
    "round_value_wires": round_value_wires,
    "jurisdiction_exposure": jurisdiction_exposure,
    "rapid_in_out": rapid_in_out,
    "profile_deviation": profile_deviation,
    "behaviour_break": behaviour_break,
    "counterparty_concentration": counterparty_concentration,
}


def run_all(customer_id: str, lookback_days: int = 90) -> list[dict]:
    """Run every detector and return the findings, triggered ones first."""
    results = [fn(customer_id, lookback_days) for fn in DETECTORS.values()]
    order = {"high": 0, "medium": 1, "low": 2, "n/a": 3}
    results.sort(key=lambda f: (not f["triggered"], order.get(f["confidence"], 3)))
    return results


# ── helpers ──────────────────────────────────────────────────────────


def _day_span(rows: list[dict]) -> int:
    """Return the inclusive day span covered by a set of transactions."""
    days = [store._as_date(t["booking_date"]) for t in rows]
    return (max(days) - min(days)).days + 1 if days else 0


def _age_years(dob: str | None) -> int | None:
    """Return an age in whole years as of the sandbox date."""
    if not dob:
        return None
    born = store._as_date(dob)
    return (store.AS_OF - born) // timedelta(days=365.2425)
