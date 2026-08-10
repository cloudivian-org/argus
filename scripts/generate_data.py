"""Generate the synthetic bank sandbox used by the Argus AML triage demo.

Everything here is fabricated. No real customer, institution, or
sanctioned party appears in this dataset, and the watchlist entries are
invented names that only *resemble* the shape of real OFAC/UN/EU records.

The dataset is deterministic (fixed seed + hand-authored scenarios) so
demo runs are reproducible and the same alert always carries the same
evidence.

Run:  python3 scripts/generate_data.py
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 20260810
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
AS_OF = date(2026, 8, 1)

rng = random.Random(SEED)


# ── helpers ──────────────────────────────────────────────────────────


def d(days_before: int) -> str:
    """Return an ISO date ``days_before`` days before the as-of date."""
    return (AS_OF - timedelta(days=days_before)).isoformat()


def txn(
    txn_id: str,
    account_id: str,
    booking_date: str,
    amount: float,
    direction: str,
    channel: str,
    counterparty: str,
    counterparty_country: str = "US",
    description: str = "",
    branch: str | None = None,
    cash: bool = False,
) -> dict:
    """Build one transaction record in the core-banking wire format."""
    return {
        "txn_id": txn_id,
        "account_id": account_id,
        "booking_date": booking_date,
        "amount": round(amount, 2),
        "currency": "USD",
        "direction": direction,  # credit = money in, debit = money out
        "channel": channel,
        "counterparty_name": counterparty,
        "counterparty_country": counterparty_country,
        "description": description,
        "branch_code": branch,
        "is_cash": cash,
    }


# ── customers ────────────────────────────────────────────────────────

CUSTOMERS = [
    {
        "customer_id": "CUS-1002",
        "legal_name": "Priya Raman",
        "customer_type": "individual",
        "date_of_birth": "1989-03-14",
        "nationality": "US",
        "residence_country": "US",
        "occupation": "Senior Software Engineer",
        "employer": "Northgate Systems Inc.",
        "segment": "retail",
        "kyc_risk_rating": "low",
        "pep_status": False,
        "onboarded": "2016-06-02",
        "last_kyc_review": "2025-06-10",
        "source_of_funds": "Salary and equity compensation",
        "expected_monthly_credit_usd": 18000,
        "expected_monthly_debit_usd": 14000,
        "declared_purpose": "Primary banking, mortgage servicing",
        "products": ["checking", "savings", "mortgage"],
    },
    {
        "customer_id": "CUS-1007",
        "legal_name": "Marcus Delgado",
        "customer_type": "individual",
        "date_of_birth": "1978-11-02",
        "nationality": "US",
        "residence_country": "US",
        "occupation": "Owner, Delgado Corner Market",
        "employer": "Self-employed",
        "segment": "retail",
        "kyc_risk_rating": "medium",
        "pep_status": False,
        "onboarded": "2011-02-17",
        "last_kyc_review": "2024-09-01",
        "source_of_funds": "Retail convenience store receipts",
        "expected_monthly_credit_usd": 25000,
        "expected_monthly_debit_usd": 22000,
        "declared_purpose": "Small business operating account",
        "products": ["business_checking"],
        "cash_intensive_business": True,
    },
    {
        "customer_id": "CUS-1019",
        "legal_name": "Meridian Polymer Trading LLC",
        "customer_type": "entity",
        "incorporation_country": "US",
        "incorporation_date": "2021-08-30",
        "industry": "Wholesale — industrial chemicals and polymers",
        "segment": "sme",
        "kyc_risk_rating": "high",
        "pep_status": False,
        "onboarded": "2021-09-15",
        "last_kyc_review": "2025-11-04",
        "source_of_funds": "Trade receivables from polymer resale",
        "expected_monthly_credit_usd": 900000,
        "expected_monthly_debit_usd": 850000,
        "declared_purpose": "Import/export settlement, supplier payments",
        "products": ["business_checking", "trade_finance", "fx"],
        "beneficial_owners": [
            {"name": "Sanjay Prakash Mehta", "ownership_pct": 60, "country": "AE"},
            {"name": "Laila Farouk Hassan", "ownership_pct": 40, "country": "AE"},
        ],
        "declared_trade_corridors": ["US", "DE", "SG"],
    },
    {
        "customer_id": "CUS-1023",
        "legal_name": "Novaterra Holdings Ltd",
        "customer_type": "entity",
        "incorporation_country": "CY",
        "incorporation_date": "2023-04-11",
        "industry": "Investment holding company",
        "segment": "corporate",
        "kyc_risk_rating": "high",
        "pep_status": True,
        "onboarded": "2023-05-20",
        "last_kyc_review": "2025-05-22",
        "source_of_funds": "Shareholder capital contribution; consultancy income",
        "expected_monthly_credit_usd": 400000,
        "expected_monthly_debit_usd": 380000,
        "declared_purpose": "Group treasury and intercompany settlement",
        "products": ["business_checking", "fx"],
        "beneficial_owners": [
            {
                "name": "Dmitri Anatolyevich Kozlov",
                "ownership_pct": 75,
                "country": "KZ",
                "pep": True,
                "pep_role": "Deputy Minister of Regional Infrastructure (2019-2024)",
            },
            {"name": "Elena Kozlova", "ownership_pct": 25, "country": "CY"},
        ],
    },
    {
        "customer_id": "CUS-1031",
        "legal_name": "Aiden Okafor",
        "customer_type": "individual",
        "date_of_birth": "2004-01-19",
        "nationality": "US",
        "residence_country": "US",
        "occupation": "Full-time student",
        "employer": "None",
        "segment": "retail",
        "kyc_risk_rating": "low",
        "pep_status": False,
        "onboarded": "2026-03-28",
        "last_kyc_review": "2026-03-28",
        "source_of_funds": "Part-time campus work, family support",
        "expected_monthly_credit_usd": 1200,
        "expected_monthly_debit_usd": 1100,
        "declared_purpose": "Everyday student banking",
        "products": ["checking"],
    },
    {
        "customer_id": "CUS-1044",
        "legal_name": "Eleanor Whitfield",
        "customer_type": "individual",
        "date_of_birth": "1948-05-30",
        "nationality": "US",
        "residence_country": "US",
        "occupation": "Retired schoolteacher",
        "employer": "Retired",
        "segment": "retail",
        "kyc_risk_rating": "low",
        "pep_status": False,
        "onboarded": "2004-02-09",
        "last_kyc_review": "2025-02-11",
        "source_of_funds": "Pension, social security, retirement savings",
        "expected_monthly_credit_usd": 4200,
        "expected_monthly_debit_usd": 3800,
        "declared_purpose": "Retirement banking and savings",
        "products": ["checking", "savings", "certificate_of_deposit"],
        "vulnerable_customer_flag": True,
    },
]

ACCOUNTS = [
    {"account_id": "ACC-2002-01", "customer_id": "CUS-1002", "product": "checking", "opened": "2016-06-02", "status": "active", "balance_usd": 21430.55},
    {"account_id": "ACC-2002-02", "customer_id": "CUS-1002", "product": "savings", "opened": "2016-06-02", "status": "active", "balance_usd": 96500.00},
    {"account_id": "ACC-2007-01", "customer_id": "CUS-1007", "product": "business_checking", "opened": "2011-02-17", "status": "active", "balance_usd": 64211.09},
    {"account_id": "ACC-2019-01", "customer_id": "CUS-1019", "product": "business_checking", "opened": "2021-09-15", "status": "active", "balance_usd": 412885.31},
    {"account_id": "ACC-2023-01", "customer_id": "CUS-1023", "product": "business_checking", "opened": "2023-05-20", "status": "active", "balance_usd": 1288430.77},
    {"account_id": "ACC-2031-01", "customer_id": "CUS-1031", "product": "checking", "opened": "2026-03-28", "status": "active", "balance_usd": 812.40},
    {"account_id": "ACC-2044-01", "customer_id": "CUS-1044", "product": "checking", "opened": "2004-02-09", "status": "active", "balance_usd": 3120.88},
    {"account_id": "ACC-2044-02", "customer_id": "CUS-1044", "product": "certificate_of_deposit", "opened": "2019-07-01", "status": "closed_early", "balance_usd": 0.00},
]


# ── transaction scenarios ────────────────────────────────────────────

transactions: list[dict] = []
n = 0


def nid() -> str:
    """Return the next sequential transaction id."""
    global n
    n += 1
    return f"TXN-{n:06d}"


# Baseline: 12 months of ordinary activity for every account, so the
# suspicious bursts sit inside real noise rather than an empty ledger.

BASELINE = {
    "ACC-2002-01": ("Northgate Systems Inc. Payroll", 9000, 2, "salary"),
    "ACC-2007-01": ("Daily merchant settlement", 780, 20, "merchant"),
    "ACC-2019-01": ("Polymer supply invoice settlement", 92000, 8, "trade"),
    "ACC-2023-01": ("Intercompany treasury transfer", 105000, 3, "treasury"),
    "ACC-2031-01": ("Campus dining wages", 410, 2, "wages"),
    "ACC-2044-01": ("Pension deposit / Social Security", 2100, 2, "pension"),
}

MERCHANTS = [
    ("Riverside Grocers", "US"), ("Metro Transit Authority", "US"),
    ("Blue Harbor Utilities", "US"), ("Sunridge Insurance", "US"),
    ("Corner Pharmacy 118", "US"), ("Lakeview Property Mgmt", "US"),
]

for acc_id, (label, amount, per_month, kind) in BASELINE.items():
    for month in range(12):
        for k in range(per_month):
            day = 30 * month + rng.randint(1, 28)
            if day > 364:
                continue
            jitter = rng.uniform(0.85, 1.15)
            transactions.append(
                txn(nid(), acc_id, d(day), amount * jitter, "credit", "ach",
                    label, "US", f"Recurring {kind} credit")
            )
            m_name, m_cc = rng.choice(MERCHANTS)
            transactions.append(
                txn(nid(), acc_id, d(max(day - 2, 1)), amount * jitter * rng.uniform(0.25, 0.6),
                    "debit", "card", m_name, m_cc, "Routine expenditure")
            )

# ---------------------------------------------------------------- 0113
# Marcus Delgado — cash structuring just under the $10,000 CTR threshold,
# spread across three branches. Classic 31 CFR 1010.313 evasion pattern.
STRUCTURING = [
    (18, 9400.00, "BR-014"), (18, 8900.00, "BR-027"), (17, 9650.00, "BR-014"),
    (16, 9200.00, "BR-041"), (15, 8750.00, "BR-027"), (14, 9800.00, "BR-014"),
    (13, 9450.00, "BR-041"), (12, 8600.00, "BR-014"), (11, 9700.00, "BR-027"),
    (10, 9150.00, "BR-041"), (8, 9900.00, "BR-014"), (7, 8400.00, "BR-027"),
    (5, 9550.00, "BR-041"), (3, 9250.00, "BR-014"),
]
for days, amt, branch in STRUCTURING:
    transactions.append(
        txn(nid(), "ACC-2007-01", d(days), amt, "credit", "branch_cash",
            "CASH DEPOSIT", "US", "Over-the-counter cash deposit",
            branch=branch, cash=True)
    )
# Funds swept out to a personal account shortly after each cluster.
for days, amt in [(16, 27000), (11, 28500), (6, 31000), (2, 24000)]:
    transactions.append(
        txn(nid(), "ACC-2007-01", d(days), amt, "debit", "internal_transfer",
            "M DELGADO PERSONAL SAVINGS", "US", "Owner draw")
    )

# ---------------------------------------------------------------- 0114
# Priya Raman — genuine home purchase. Large, but fully explained by the
# counterparty types. This alert SHOULD be closed as a false positive.
transactions.append(
    txn(nid(), "ACC-2002-01", d(22), 310000.00, "credit", "wire",
        "FIRST MERIDIAN TITLE COMPANY LLC", "US",
        "Proceeds of sale - 44 Alder St closing, file 2026-A8831")
)
transactions.append(
    txn(nid(), "ACC-2002-01", d(19), 295400.00, "debit", "wire",
        "CASCADE ESCROW SERVICES INC", "US",
        "Purchase funds - 1180 Kestrel Ln closing, file 2026-C1204")
)
transactions.append(
    txn(nid(), "ACC-2002-01", d(18), 12800.00, "debit", "ach",
        "NORTHGATE MORTGAGE SERVICING", "US", "Mortgage payoff - loan 88123441")
)

# ---------------------------------------------------------------- 0115
# Meridian Polymer — round-dollar wires to a jurisdiction outside the
# declared trade corridor, to a counterparty that fuzzy-matches an SDN
# entry. Invoice values do not reconcile to shipment records.
TBML = [
    (58, "ZARIN PETROCHEMICAL FZE", "AE", "INV MPT-4471 polymer resin"),
    (51, "ZARIN PETROCHEMICAL FZE", "AE", "INV MPT-4472 polymer resin"),
    (44, "ASTANA KAZ TRADE LLP", "KZ", "INV MPT-4488 additive compound"),
    (37, "ZARIN PETROCHEMICAL FZE", "AE", "INV MPT-4491 polymer resin"),
    (30, "ASTANA KAZ TRADE LLP", "KZ", "INV MPT-4502 additive compound"),
    (23, "ZARIN PETROCHEMICAL FZE", "AE", "INV MPT-4519 polymer resin"),
]
for days, cp, cc, desc in TBML:
    transactions.append(
        txn(nid(), "ACC-2019-01", d(days), 250000.00, "debit", "wire", cp, cc, desc)
    )
for days, amt in [(60, 268000), (46, 271500), (32, 264000), (25, 259000)]:
    transactions.append(
        txn(nid(), "ACC-2019-01", d(days), amt, "credit", "wire",
            "GULF LINE COMMODITIES DMCC", "AE", "Advance against proforma invoice")
    )

# ---------------------------------------------------------------- 0116
# Aiden Okafor — funnel / mule account. Many small unrelated inbound
# credits, near-total pass-through to ATM cash and a crypto off-ramp.
MULE_SENDERS = [
    "R. Castellanos", "T. Nguyen", "B. Okonkwo", "J. Alvarez", "S. Petrov",
    "M. Haddad", "L. Fernandes", "K. Oyelaran", "D. Whitmore", "A. Basu",
    "P. Sorensen", "C. Mbeki", "F. Duarte", "H. Yilmaz", "N. Kaur",
    "G. Rossi", "V. Ivanov", "E. Adeyemi", "O. Kim", "W. Zhang",
    "Q. Silva", "Z. Farah", "I. Novak", "U. Bello", "Y. Tanaka",
    "X. Moreau", "R. Grewal", "T. Abara", "J. Lindqvist", "S. Osei",
    "B. Ferreira",
]
mule_total = 0.0
for i in range(47):
    sender = MULE_SENDERS[i % len(MULE_SENDERS)]
    amt = round(rng.uniform(200, 1900), 2)
    day = 26 - (i * 26 // 47)
    mule_total += amt
    transactions.append(
        txn(nid(), "ACC-2031-01", d(max(day, 1)), amt, "credit", "p2p",
            sender, "US", "Instant P2P transfer received")
    )
# 94% out within 24 hours: ATM cash + crypto exchange.
out_remaining = mule_total * 0.94
for i in range(21):
    day = max(25 - (i * 25 // 21), 1)
    amt = round(out_remaining / 21 * rng.uniform(0.8, 1.2), 2)
    if i % 3 == 0:
        transactions.append(
            txn(nid(), "ACC-2031-01", d(day), amt, "debit", "crypto_exchange",
                "HELIOSPAY DIGITAL ASSETS LTD", "SC",
                "Purchase of digital assets")
        )
    else:
        transactions.append(
            txn(nid(), "ACC-2031-01", d(day), amt, "debit", "atm",
                "ATM WITHDRAWAL", "US", "ATM cash withdrawal", branch="ATM-8802",
                cash=True)
        )

# ---------------------------------------------------------------- 0117
# Eleanor Whitfield — elder financial exploitation. Long-dormant profile
# breaks abruptly: CD broken at a penalty, then serial outbound wires to
# a single overseas corridor and a crypto off-ramp.
transactions.append(
    txn(nid(), "ACC-2044-01", d(74), 142000.00, "credit", "internal_transfer",
        "CD EARLY REDEMPTION ACC-2044-02", "US",
        "Certificate of deposit broken before maturity - penalty 3,180.00 applied")
)
ELDER = [
    (71, 24000.00, "ADEBAYO K MENSAH", "GH", "Family emergency support"),
    (66, 19500.00, "ADEBAYO K MENSAH", "GH", "Medical costs"),
    (60, 22000.00, "GOLDCOAST VENTURES LTD", "GH", "Investment contribution"),
    (52, 18000.00, "ADEBAYO K MENSAH", "GH", "Legal fees"),
    (45, 26500.00, "GOLDCOAST VENTURES LTD", "GH", "Investment contribution"),
    (38, 15000.00, "HELIOSPAY DIGITAL ASSETS LTD", "SC", "Digital asset purchase"),
    (29, 21000.00, "ADEBAYO K MENSAH", "GH", "Customs release fee"),
    (17, 19000.00, "HELIOSPAY DIGITAL ASSETS LTD", "SC", "Digital asset purchase"),
    (6, 19000.00, "ADEBAYO K MENSAH", "GH", "Final transfer fee"),
]
for days, amt, cp, cc, desc in ELDER:
    channel = "crypto_exchange" if "HELIOSPAY" in cp else "wire"
    transactions.append(
        txn(nid(), "ACC-2044-01", d(days), amt, "debit", channel, cp, cc, desc)
    )

# ---------------------------------------------------------------- 0118
# Novaterra Holdings — PEP-controlled layering through related shells,
# with the classic in-and-straight-out corporate structure.
LAYERING = [
    (84, 480000.00, "credit", "ALTAI CONSULTING SERVICES LP", "GB", "Consultancy retainer"),
    (83, 470000.00, "debit", "STELLARIS TRADE PARTNERS LTD", "AE", "Intercompany advance"),
    (69, 525000.00, "credit", "ALTAI CONSULTING SERVICES LP", "GB", "Consultancy retainer"),
    (68, 515000.00, "debit", "BLUEPOINT CAPITAL SARL", "LU", "Intercompany advance"),
    (54, 610000.00, "credit", "KAZINFRA REGIONAL PROJECTS JSC", "KZ", "Advisory fee settlement"),
    (53, 598000.00, "debit", "STELLARIS TRADE PARTNERS LTD", "AE", "Intercompany advance"),
    (40, 555000.00, "credit", "KAZINFRA REGIONAL PROJECTS JSC", "KZ", "Advisory fee settlement"),
    (39, 544000.00, "debit", "BLUEPOINT CAPITAL SARL", "LU", "Intercompany advance"),
    (21, 690000.00, "credit", "KAZINFRA REGIONAL PROJECTS JSC", "KZ", "Advisory fee settlement"),
    (20, 675000.00, "debit", "STELLARIS TRADE PARTNERS LTD", "AE", "Intercompany advance"),
]
for days, amt, direction, cp, cc, desc in LAYERING:
    transactions.append(
        txn(nid(), "ACC-2023-01", d(days), amt, direction, "wire", cp, cc, desc)
    )

transactions.sort(key=lambda t: (t["booking_date"], t["txn_id"]))


# ── alerts ───────────────────────────────────────────────────────────

ALERTS = [
    {
        "alert_id": "ALT-2026-0113",
        "created": d(2),
        "status": "open",
        "priority": "high",
        "customer_id": "CUS-1007",
        "account_ids": ["ACC-2007-01"],
        "detection_rule": "STRUCT-01",
        "rule_description": "Multiple cash deposits below the CTR reporting threshold within a rolling 30-day window",
        "rule_threshold": "3+ cash deposits between $8,000 and $10,000 in 30 days",
        "system": "Transaction Monitoring (batch)",
        "lookback_days": 30,
        "raw_score": 78,
        "analyst_queue": "L1-FIU-CASH",
    },
    {
        "alert_id": "ALT-2026-0114",
        "created": d(17),
        "status": "open",
        "priority": "medium",
        "customer_id": "CUS-1002",
        "account_ids": ["ACC-2002-01"],
        "detection_rule": "THRESH-01",
        "rule_description": "Single transaction value exceeds 10x the customer's expected monthly turnover",
        "rule_threshold": "value > 10x expected_monthly_credit_usd",
        "system": "Transaction Monitoring (real-time)",
        "lookback_days": 30,
        "raw_score": 55,
        "analyst_queue": "L1-FIU-RETAIL",
    },
    {
        "alert_id": "ALT-2026-0115",
        "created": d(21),
        "status": "open",
        "priority": "critical",
        "customer_id": "CUS-1019",
        "account_ids": ["ACC-2019-01"],
        "detection_rule": "HRJ-02",
        "rule_description": "Round-value cross-border wires to a jurisdiction outside the customer's declared trade corridors",
        "rule_threshold": "3+ round-value wires >= $100,000 to non-declared corridor in 90 days",
        "system": "Transaction Monitoring (batch)",
        "lookback_days": 90,
        "raw_score": 91,
        "analyst_queue": "L1-FIU-TRADE",
    },
    {
        "alert_id": "ALT-2026-0116",
        "created": d(1),
        "status": "open",
        "priority": "high",
        "customer_id": "CUS-1031",
        "account_ids": ["ACC-2031-01"],
        "detection_rule": "PASSTHRU-05",
        "rule_description": "High inbound P2P count from unrelated senders with near-total same-day outflow on a newly opened account",
        "rule_threshold": "pass-through ratio > 0.80 and unique senders >= 10 in 30 days",
        "system": "Transaction Monitoring (real-time)",
        "lookback_days": 30,
        "raw_score": 88,
        "analyst_queue": "L1-FIU-FRAUD",
    },
    {
        "alert_id": "ALT-2026-0117",
        "created": d(5),
        "status": "open",
        "priority": "high",
        "customer_id": "CUS-1044",
        "account_ids": ["ACC-2044-01", "ACC-2044-02"],
        "detection_rule": "VULN-03",
        "rule_description": "Abrupt change in activity for a long-tenured customer aged 70+, including early term-deposit redemption and serial cross-border outflows",
        "rule_threshold": "activity deviation > 5 sigma from 24-month baseline with vulnerable-customer flag",
        "system": "Behavioural Analytics",
        "lookback_days": 90,
        "raw_score": 84,
        "analyst_queue": "L1-FIU-RETAIL",
        "branch_note": "Branch staff at BR-014 recorded that the customer declined to state the purpose of the 12 June wire and became agitated when asked. Customer mentioned an overseas 'fiance' she has not met in person.",
    },
    {
        "alert_id": "ALT-2026-0118",
        "created": d(19),
        "status": "open",
        "priority": "critical",
        "customer_id": "CUS-1023",
        "account_ids": ["ACC-2023-01"],
        "detection_rule": "LAYER-07",
        "rule_description": "Funds received and forwarded within 48 hours to related entities with no apparent economic purpose, on a PEP-controlled account",
        "rule_threshold": "in/out matching >= 90% within 48h across 3+ related counterparties",
        "system": "Network Analytics",
        "lookback_days": 90,
        "raw_score": 93,
        "analyst_queue": "L2-FIU-EDD",
    },
]


# ── screening lists ──────────────────────────────────────────────────
# Invented entries shaped like real sanctions/PEP records. No real
# designated person or entity is represented here.

WATCHLIST = [
    {
        "list_id": "SDN-SIM-4471",
        "list_name": "OFAC SDN (simulated)",
        "entity_name": "ZARIN PETROCHEMICAL FZCO",
        "aliases": ["ZARIN PETROCHEM FZCO", "ZARIN PETROCHEMICAL FREE ZONE CO"],
        "entity_type": "entity",
        "country": "AE",
        "programs": ["SIM-NPWMD"],
        "listed_date": "2024-11-19",
        "remarks": "Designated for acting on behalf of a sanctioned petrochemical network (simulated record).",
    },
    {
        "list_id": "SDN-SIM-2210",
        "list_name": "OFAC SDN (simulated)",
        "entity_name": "HELIOSPAY DIGITAL ASSETS LTD",
        "aliases": ["HELIOSPAY", "HELIOS PAY DIGITAL"],
        "entity_type": "entity",
        "country": "SC",
        "programs": ["SIM-CYBER"],
        "listed_date": "2025-07-02",
        "remarks": "Virtual asset service provider identified as a laundering conduit for fraud proceeds (simulated record).",
    },
    {
        "list_id": "UN-SIM-0912",
        "list_name": "UN Consolidated (simulated)",
        "entity_name": "ASTANA KAZ TRADE LLP",
        "aliases": ["ASTANA KAZTRADE"],
        "entity_type": "entity",
        "country": "KZ",
        "programs": ["SIM-PROLIF"],
        "listed_date": "2025-02-14",
        "remarks": "Front company for restricted dual-use goods procurement (simulated record).",
    },
    {
        "list_id": "PEP-SIM-3390",
        "list_name": "Global PEP register (simulated)",
        "entity_name": "DMITRI ANATOLYEVICH KOZLOV",
        "aliases": ["D. A. KOZLOV", "DMITRIY KOZLOV"],
        "entity_type": "individual",
        "country": "KZ",
        "programs": ["PEP-DOMESTIC"],
        "listed_date": "2019-03-01",
        "remarks": "Deputy Minister of Regional Infrastructure 2019-2024; family members also listed (simulated record).",
    },
    {
        "list_id": "PEP-SIM-3391",
        "list_name": "Global PEP register (simulated)",
        "entity_name": "ELENA KOZLOVA",
        "aliases": ["E. KOZLOVA"],
        "entity_type": "individual",
        "country": "CY",
        "programs": ["PEP-RCA"],
        "listed_date": "2019-03-01",
        "remarks": "Relative/close associate of a listed PEP (simulated record).",
    },
    {
        "list_id": "INT-SIM-0055",
        "list_name": "Internal high-risk register (simulated)",
        "entity_name": "GOLDCOAST VENTURES LTD",
        "aliases": ["GOLD COAST VENTURES"],
        "entity_type": "entity",
        "country": "GH",
        "programs": ["INTERNAL-FRAUD"],
        "listed_date": "2026-01-08",
        "remarks": "Named as a beneficiary account in three prior romance-fraud reports (simulated record).",
    },
]

ADVERSE_MEDIA = [
    {
        "article_id": "AM-0001",
        "published": "2026-02-11",
        "source": "Gulf Trade Wire (simulated outlet)",
        "headline": "Free-zone chemical trader accused of re-invoicing scheme",
        "subject_names": ["Zarin Petrochemical FZE", "Zarin Petrochemical FZCO"],
        "summary": "Regional customs authorities allege a Jebel Ali free-zone chemicals trader systematically over-invoiced polymer shipments to move value out of the region. The company denies wrongdoing.",
        "risk_tags": ["trade-based money laundering", "customs fraud"],
        "reliability": "medium",
    },
    {
        "article_id": "AM-0002",
        "published": "2025-09-30",
        "source": "Central Asia Monitor (simulated outlet)",
        "headline": "Former deputy minister's family linked to Cyprus holding structure",
        "subject_names": ["Dmitri Anatolyevich Kozlov", "Novaterra Holdings Ltd"],
        "summary": "An investigative outlet reports that infrastructure contracts awarded during the tenure of a former deputy minister were followed by consultancy payments routed through a Cyprus holding company connected to his family.",
        "risk_tags": ["corruption", "PEP", "shell structure"],
        "reliability": "high",
    },
    {
        "article_id": "AM-0003",
        "published": "2026-04-22",
        "source": "Consumer Protection Bulletin (simulated outlet)",
        "headline": "Regulator warns on Ghana-corridor romance fraud targeting retirees",
        "subject_names": ["Goldcoast Ventures Ltd"],
        "summary": "A consumer regulator warned that victims of romance fraud are being directed to wire funds to a small set of Accra-based corporate beneficiaries, one of which appears repeatedly in victim complaints.",
        "risk_tags": ["romance fraud", "elder exploitation"],
        "reliability": "high",
    },
    {
        "article_id": "AM-0004",
        "published": "2025-08-05",
        "source": "Chain Analytics Daily (simulated outlet)",
        "headline": "Offshore exchange named as top cash-out venue for mule networks",
        "subject_names": ["HeliosPay Digital Assets Ltd"],
        "summary": "Blockchain analytics researchers named a Seychelles-registered exchange as the largest single off-ramp for funds traced from domestic money-mule networks.",
        "risk_tags": ["money mule", "virtual assets"],
        "reliability": "high",
    },
    {
        "article_id": "AM-0005",
        "published": "2024-05-16",
        "source": "Regional Business Journal (simulated outlet)",
        "headline": "Corner Market owner honoured by chamber of commerce",
        "subject_names": ["Marcus Delgado"],
        "summary": "A local convenience store owner received a small-business service award from the regional chamber of commerce.",
        "risk_tags": [],
        "reliability": "medium",
    },
]

PRIOR_CASES = [
    {
        "case_id": "CASE-2024-0771",
        "customer_id": "CUS-1007",
        "opened": "2024-08-14",
        "closed": "2024-09-02",
        "alert_ids": ["ALT-2024-0669"],
        "detection_rule": "STRUCT-01",
        "disposition": "closed_no_sar",
        "rationale": "Cash deposits consistent with documented convenience-store receipts; deposit sizes were irregular and not clustered below the threshold.",
        "sar_filed": False,
    },
    {
        "case_id": "CASE-2025-1902",
        "customer_id": "CUS-1019",
        "opened": "2025-10-03",
        "closed": "2025-10-30",
        "alert_ids": ["ALT-2025-1533"],
        "detection_rule": "HRJ-02",
        "disposition": "closed_with_edd",
        "rationale": "Wires to a non-declared corridor were explained as a one-off supplier substitution. Enhanced due diligence applied; customer undertook to update declared corridors.",
        "sar_filed": False,
        "follow_up": "Customer never updated declared trade corridors.",
    },
    {
        "case_id": "CASE-2026-0210",
        "customer_id": "CUS-1023",
        "opened": "2026-01-19",
        "closed": "2026-02-06",
        "alert_ids": ["ALT-2026-0044"],
        "detection_rule": "LAYER-07",
        "disposition": "escalated_l2",
        "rationale": "Layering pattern noted; L2 requested source-of-wealth evidence for the PEP beneficial owner. Evidence provided was a single unaudited letter.",
        "sar_filed": False,
        "follow_up": "Source-of-wealth documentation remains outstanding.",
    },
]

# High-risk jurisdiction reference (simulated stand-in for the FATF
# grey/black lists plus the bank's own internal risk ratings).
JURISDICTIONS = {
    "US": {"name": "United States", "risk": "low"},
    "GB": {"name": "United Kingdom", "risk": "low"},
    "DE": {"name": "Germany", "risk": "low"},
    "SG": {"name": "Singapore", "risk": "low"},
    "LU": {"name": "Luxembourg", "risk": "medium", "note": "Corporate secrecy / holding-company concentration"},
    "CY": {"name": "Cyprus", "risk": "medium", "note": "Shell-company incorporation risk"},
    "AE": {"name": "United Arab Emirates", "risk": "high", "note": "Free-zone trade re-invoicing risk"},
    "KZ": {"name": "Kazakhstan", "risk": "high", "note": "Procurement / dual-use diversion risk"},
    "GH": {"name": "Ghana", "risk": "high", "note": "Elevated advance-fee and romance-fraud corridor"},
    "SC": {"name": "Seychelles", "risk": "high", "note": "Offshore VASP registration, limited transparency"},
}


def write(name: str, payload: object) -> None:
    """Write one JSON file into the data directory."""
    path = DATA_DIR / name
    path.write_text(json.dumps(payload, indent=2) + "\n")
    size = len(payload) if isinstance(payload, list) else len(payload)  # type: ignore[arg-type]
    print(f"  {path.name:24s} {size:5d} records")


def main() -> None:
    """Write every synthetic dataset file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating synthetic bank sandbox (seed={SEED}, as-of={AS_OF})")
    write("customers.json", CUSTOMERS)
    write("accounts.json", ACCOUNTS)
    write("transactions.json", transactions)
    write("alerts.json", ALERTS)
    write("watchlist.json", WATCHLIST)
    write("adverse_media.json", ADVERSE_MEDIA)
    write("prior_cases.json", PRIOR_CASES)
    write("jurisdictions.json", JURISDICTIONS)
    print("Done. All records are fabricated; no real person or entity is represented.")


if __name__ == "__main__":
    main()
