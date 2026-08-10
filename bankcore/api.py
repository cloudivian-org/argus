"""Shared tool bodies.

Each agent in the bundle discovers tools from its own ``tools/python/``
directory, which is how least privilege is expressed: the screening
analyst simply has no ledger-write tool to call. The behaviour behind
those tools should not be duplicated per agent, so the bodies live here
and every ``@tool`` file is a thin wrapper carrying only the signature,
the docstring, and the delegation.
"""

from __future__ import annotations

from collections import defaultdict

from . import casefile, store, typologies

MAX_TXN_ROWS = 120


def alert_context(alert_id: str) -> dict:
    """Return an alert with its customer thumbnail and in-scope accounts."""
    alert = store.get_alert(alert_id)
    if not alert:
        return {
            "error": f"Unknown alert_id {alert_id!r}",
            "known_alert_ids": [a["alert_id"] for a in store.alerts()],
        }
    customer = store.get_customer(alert["customer_id"]) or {}
    flags = []
    if customer.get("pep_status"):
        flags.append("PEP")
    if customer.get("vulnerable_customer_flag"):
        flags.append("VULNERABLE CUSTOMER")
    if customer.get("cash_intensive_business"):
        flags.append("cash-intensive business")
    return {
        "summary": (
            f"{alert['alert_id']} · {alert['priority'].upper()} priority · rule "
            f"{alert['detection_rule']} · {customer.get('legal_name')} "
            f"({alert['customer_id']}, {customer.get('segment')}, "
            f"{customer.get('kyc_risk_rating')} KYC risk"
            + (f", {', '.join(flags)}" if flags else "")
            + f") · raised {alert['created']} · {alert['lookback_days']}-day window"
            + f" · detected: {alert['rule_description']}"
        ),
        "alert": alert,
        "customer_thumbnail": {
            "customer_id": alert["customer_id"],
            "legal_name": customer.get("legal_name"),
            "customer_type": customer.get("customer_type"),
            "segment": customer.get("segment"),
            "kyc_risk_rating": customer.get("kyc_risk_rating"),
            "pep_status": customer.get("pep_status"),
            "vulnerable_customer_flag": customer.get("vulnerable_customer_flag", False),
        },
        "accounts_in_scope": [
            a for a in store.accounts_for(alert["customer_id"])
            if a["account_id"] in alert["account_ids"]
        ],
        "as_of_date": store.AS_OF.isoformat(),
    }


def alert_queue(priority: str | None = None) -> dict:
    """Return the triage queue with a disposition marker per alert."""
    rows = []
    for alert in sorted(store.alerts(), key=lambda a: a["created"], reverse=True):
        if priority and alert["priority"] != priority:
            continue
        customer = store.get_customer(alert["customer_id"]) or {}
        existing = casefile.read_case(alert["alert_id"])
        rows.append(
            {
                "alert_id": alert["alert_id"],
                "created": alert["created"],
                "priority": alert["priority"],
                "detection_rule": alert["detection_rule"],
                "rule_description": alert["rule_description"],
                "customer_id": alert["customer_id"],
                "customer_name": customer.get("legal_name"),
                "segment": customer.get("segment"),
                "kyc_risk_rating": customer.get("kyc_risk_rating"),
                "queue": alert["analyst_queue"],
                "already_dispositioned": bool(existing),
                "recorded_disposition": (existing or {}).get("disposition"),
            }
        )
    waiting = sum(1 for r in rows if not r["already_dispositioned"])
    lines = [
        f"  {r['alert_id']}  {r['priority']:<8} {r['detection_rule']:<12} "
        f"{(r['customer_name'] or '')[:28]:<30} "
        + ("already dispositioned: " + str(r["recorded_disposition"])
           if r["already_dispositioned"] else "awaiting triage")
        for r in rows
    ]
    return {
        "summary": (
            f"{len(rows)} alert(s) in the queue, {waiting} awaiting triage "
            f"(as of {store.AS_OF.isoformat()}):\n" + "\n".join(lines)
        ),
        "as_of_date": store.AS_OF.isoformat(),
        "queue_depth": len(rows),
        "awaiting_triage": waiting,
        "alerts": rows,
    }


def customer_profile(customer_id: str) -> dict:
    """Return the KYC profile, accounts, and a review-currency check."""
    customer = store.get_customer(customer_id)
    if not customer:
        return {
            "error": f"Unknown customer_id {customer_id!r}",
            "known_customer_ids": [c["customer_id"] for c in store.customers()],
        }
    last_review = customer.get("last_kyc_review")
    review_age_days = store.days_ago(last_review) if last_review else None
    country = customer.get("residence_country") or customer.get("incorporation_country")
    owners = customer.get("beneficial_owners", [])
    who = (
        f"{customer.get('occupation')}"
        if customer.get("customer_type") == "individual"
        else f"{customer.get('industry')}"
    )
    return {
        "summary": (
            f"{customer.get('legal_name')} ({customer_id}) · "
            f"{customer.get('customer_type')} · {customer.get('segment')} · "
            f"{customer.get('kyc_risk_rating')} KYC risk · {who} · "
            f"customer since {customer.get('onboarded')} · "
            f"declared source of funds: {customer.get('source_of_funds')} · "
            f"expects ${float(customer.get('expected_monthly_credit_usd', 0)):,.0f}/mo in and "
            f"${float(customer.get('expected_monthly_debit_usd', 0)):,.0f}/mo out · "
            f"last KYC review {last_review} ("
            + (
                f"{review_age_days} days ago — STALE, over 12 months"
                if review_age_days and review_age_days > 365
                else f"{review_age_days} days ago, current"
            )
            + ")"
            + (
                " · beneficial owners: "
                + "; ".join(
                    f"{o['name']} {o.get('ownership_pct')}% ({o.get('country')})"
                    + (" PEP" if o.get("pep") else "")
                    for o in owners
                )
                if owners else ""
            )
            + (" · VULNERABLE CUSTOMER" if customer.get("vulnerable_customer_flag") else "")
        ),
        "customer": customer,
        "accounts": store.accounts_for(customer_id),
        "kyc_currency": {
            "last_kyc_review": last_review,
            "review_age_days": review_age_days,
            "is_stale": bool(review_age_days and review_age_days > 365),
            "note": (
                "A periodic review older than 12 months means the declared "
                "expectations below may no longer reflect the agreed relationship."
            ),
        },
        "home_country_risk": store.country_risk(country) if country else "unknown",
        "beneficial_owners": customer.get("beneficial_owners", []),
    }


def transactions_query(
    customer_id: str,
    lookback_days: int = 90,
    direction: str | None = None,
    min_amount: float | None = None,
    account_id: str | None = None,
    channel: str | None = None,
) -> dict:
    """Return filtered transactions plus aggregates over the full match set."""
    rows = store.txns_for(
        customer_id,
        lookback_days=lookback_days,
        account_id=account_id,
        min_amount=min_amount,
        direction=direction,
    )
    if channel:
        rows = [t for t in rows if t["channel"] == channel]

    by_channel: dict[str, dict] = defaultdict(lambda: {"count": 0, "total_usd": 0.0})
    by_country: dict[str, dict] = defaultdict(lambda: {"count": 0, "total_usd": 0.0})
    credit_total = debit_total = 0.0
    for t in rows:
        by_channel[t["channel"]]["count"] += 1
        by_channel[t["channel"]]["total_usd"] += t["amount"]
        by_country[t["counterparty_country"]]["count"] += 1
        by_country[t["counterparty_country"]]["total_usd"] += t["amount"]
        if t["direction"] == "credit":
            credit_total += t["amount"]
        else:
            debit_total += t["amount"]

    def rounded(mapping: dict) -> dict:
        return {
            k: {"count": v["count"], "total_usd": round(v["total_usd"], 2)}
            for k, v in sorted(mapping.items(), key=lambda kv: -kv[1]["total_usd"])
        }

    channel_bits = ", ".join(
        f"{k} {v['count']}x ${v['total_usd']:,.0f}" for k, v in list(rounded(by_channel).items())[:4]
    )
    risky = [
        f"{cc} ${v['total_usd']:,.0f}"
        for cc, v in rounded(by_country).items()
        if store.country_risk(cc) == "high"
    ]
    return {
        "summary": (
            f"{len(rows)} transaction(s) for {customer_id} over {lookback_days} days"
            + (f" [{direction} only]" if direction else "")
            + (f" [{channel} only]" if channel else "")
            + f" · ${credit_total:,.2f} in, ${debit_total:,.2f} out"
            + (f" · channels: {channel_bits}" if channel_bits else "")
            + (f" · HIGH-RISK JURISDICTIONS: {', '.join(risky)}" if risky else "")
            + (f" · showing first {MAX_TXN_ROWS} rows" if len(rows) > MAX_TXN_ROWS else "")
        ),
        "customer_id": customer_id,
        "filters": {
            "lookback_days": lookback_days,
            "direction": direction,
            "min_amount": min_amount,
            "account_id": account_id,
            "channel": channel,
        },
        "aggregates": {
            "matched_transactions": len(rows),
            "total_credits_usd": round(credit_total, 2),
            "total_debits_usd": round(debit_total, 2),
            "by_channel": rounded(by_channel),
            "by_counterparty_country": {
                cc: {**v, "country_risk": store.country_risk(cc)}
                for cc, v in rounded(by_country).items()
            },
        },
        "rows_returned": min(len(rows), MAX_TXN_ROWS),
        "truncated": len(rows) > MAX_TXN_ROWS,
        "transactions": rows[:MAX_TXN_ROWS],
    }


def typology_report(
    customer_id: str,
    lookback_days: int = 90,
    typology: str | None = None,
) -> dict:
    """Run one or every typology detector and return the findings."""
    if typology:
        fn = typologies.DETECTORS.get(typology)
        if not fn:
            return {
                "error": f"Unknown typology {typology!r}",
                "available": sorted(typologies.DETECTORS),
            }
        findings = [fn(customer_id, lookback_days)]
    else:
        findings = typologies.run_all(customer_id, lookback_days)

    triggered = [f for f in findings if f["triggered"]]
    cleared = [f for f in findings if not f["triggered"]]
    detail = "\n".join(
        f"  TRIGGERED [{f['confidence']:>6} confidence]  {f['typology']}\n"
        f"      {f['summary']}"
        for f in triggered
    )
    ruled_out = "\n".join(f"  cleared  {f['typology']} — {f['summary']}" for f in cleared)
    return {
        "summary": (
            f"{len(triggered)} of {len(findings)} detectors triggered for {customer_id} "
            f"over {lookback_days} days.\n"
            + (detail + "\n" if detail else "")
            + (f"Ruled out:\n{ruled_out}" if ruled_out else "")
        ),
        "customer_id": customer_id,
        "lookback_days": lookback_days,
        "detectors_run": len(findings),
        "triggered_count": len(triggered),
        "triggered_typologies": [f["typology"] for f in triggered],
        "findings": findings,
        "note": (
            "Detector output is the evidentiary record. Cite figures from `metrics` "
            "and transaction ids from `evidence_txn_ids`; do not estimate, round "
            "beyond the given precision, or introduce numbers no detector produced."
        ),
    }


def prior_case_history(customer_id: str) -> dict:
    """Return prior investigations, SAR history, and outstanding follow-ups."""
    cases = [c for c in store.prior_cases() if c["customer_id"] == customer_id]
    outstanding = [c for c in cases if c.get("follow_up")]
    history = "\n".join(
        f"  {c['case_id']} ({c['opened']} → {c['closed']}) rule {c['detection_rule']} "
        f"→ {c['disposition']}"
        + (f" · OUTSTANDING: {c['follow_up']}" if c.get("follow_up") else "")
        for c in sorted(cases, key=lambda c: c["opened"], reverse=True)
    )
    return {
        "summary": (
            f"{len(cases)} prior case(s) for {customer_id}, "
            f"{sum(1 for c in cases if c.get('sar_filed'))} prior SAR(s), "
            f"{len(outstanding)} outstanding follow-up(s)."
            + (f"\n{history}" if history else " No investigation history.")
        ),
        "customer_id": customer_id,
        "prior_case_count": len(cases),
        "prior_sar_count": sum(1 for c in cases if c.get("sar_filed")),
        "outstanding_follow_ups": [
            {"case_id": c["case_id"], "follow_up": c["follow_up"]} for c in outstanding
        ],
        "cases": sorted(cases, key=lambda c: c["opened"], reverse=True),
        "note": (
            "A repeat alert on the same detection rule, or an incomplete remediation "
            "from a prior case, must be addressed explicitly in the disposition."
        ),
    }
