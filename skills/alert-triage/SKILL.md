---
name: alert-triage
description: >-
  The end-to-end procedure for triaging one transaction-monitoring alert:
  scoping, parallel investigation, scoring, disposition, and the evidence
  standard a case file has to meet. Load this at the start of any triage.
---

# Alert triage procedure

## 0. What a triage decision actually is

You are deciding one thing: **is there a reasonable basis to suspect that
this activity involves funds derived from illegal activity, is designed to
evade a reporting requirement, has no business or apparent lawful purpose, or
otherwise indicates the use of the bank to facilitate criminal activity?**

That is the statutory test. Not "does this look weird". Weird is the *start*
of the question. Most weird activity is a customer doing something ordinary
that the monitoring rule was too crude to recognise.

Two failure directions, both expensive:

- **Under-report** — a genuine pattern closed. Regulatory failure, potential
  enforcement action, real crime unreported.
- **Over-report** — a false positive escalated. Buries genuine reports in
  volume, consumes the financial intelligence unit's finite capacity, and
  subjects a customer to consequences they did not earn.

An analyst who escalates everything is not being careful. They are moving
their own risk onto someone else.

## 1. Scope before you investigate

`get_alert` → `get_customer_profile` → `get_prior_cases`.

Answer these before pulling a single transaction:

- What did the rule *actually* detect? Read `rule_description` and
  `rule_threshold`. A threshold rule firing on one large payment is a
  different question from a pattern rule firing on fourteen.
- What did the customer tell the bank to expect? Occupation or industry,
  declared source of funds, expected turnover, declared corridors.
- How current is that expectation? A KYC review older than twelve months
  means the baseline may simply be stale rather than the activity abnormal.
- Has this happened before? Which rule, what disposition, was any agreed
  remediation actually delivered?
- Is there a branch note? Human observation of customer demeanour is
  frequently the single most probative item in the whole file.

## 2. Fan out in parallel

Dispatch `financial_investigator` and `screening_analyst` in the **same
turn**. They are independent and they run concurrently; serialising them
doubles the wall-clock for no benefit.

Give each specific questions, not a generic instruction. "Establish whether
the cash deposits cluster below the reporting threshold and whether the
timing suggests deliberate splitting" gets you an answer. "Investigate this
customer" gets you a summary you already have.

## 3. Score, then read the factors

`score_alert_risk` runs every detector, screens the whole counterparty
network, and adds static customer risk and case history under per-category
ceilings.

**Read the factor list, not just the total.** Two alerts scoring 80 can be
completely different cases — one carrying a sanctions match, another
carrying an accumulation of behavioural signals. The factors tell you which
one you have.

The band is advisory:

| Score | Band | Recommended |
|---|---|---|
| 80-100 | critical | `recommend_sar` |
| 60-79 | high | `escalate_l2` |
| 35-59 | medium | `close_with_edd` |
| 0-34 | low | `close_no_sar` |

You may depart from it. Sometimes you should — a scorecard cannot read a
branch note. But a departure has to be written down and argued, and
`record_disposition` will refuse the write until it is.

## 4. Decide

- `close_no_sar` — activity explained, corroborated, consistent with the
  profile. Write the rationale strongly enough that nobody re-opens it.
- `close_with_edd` — no reasonable basis to suspect, but the profile needs
  refreshing or the activity needs watching. Name the specific EDD action.
- `escalate_l2` — a reasonable basis may exist and the decision needs a
  senior investigator, or the case needs evidence you cannot obtain.
- `recommend_sar` — a reasonable basis to suspect exists and the case is
  documented well enough to support a filing.

## 5. The evidence standard

Every figure traces to a tool result. Not "approximately", not "around",
not a number you carried forward from three messages ago and adjusted.

Every cited transaction id exists on this customer's accounts —
`record_disposition` and `submit_sar_draft` both verify this and reject
drafts that fail.

Every typology is addressed, including the ones you ruled out. A triage that
lists only what it found does not show that you looked for anything else.

Exculpatory evidence appears in the rationale. If the packs contain
something arguing against your conclusion, engage with it. Omitting it is
how a case falls apart under challenge.

## 6. Challenge before you record

Dispatch `qc_reviewer` with your draft, your proposed disposition, and your
reasoning. When it says a figure is unsupported, fix the figure — do not
argue it through. That exchange is the control working.

## 7. Record

`submit_sar_draft` first where there is a draft, then `record_disposition`.
Both pause for human approval. That pause is the maker-checker control, not
a failure — wait for it.

Finish with `verify_audit_ledger` so the human can see the hash chain is
intact.

## What this system cannot do, by design

- It cannot file a SAR. Drafts sit in `pending_human_review`.
- It cannot close an alert in the bank's system of record.
- It cannot contact the customer. The tipping-off control denies the call.
- It cannot write to the case record without a human approving that write.

Say so in your final report. A customer evaluating this needs to know where
the machine stops and a person starts.
