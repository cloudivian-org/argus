# Argus — proposal notes for a bank conversation

Supporting material for presenting the Argus AML triage bundle. The README
covers what it is and how to run it; this covers how to talk about it.

---

## The one-sentence pitch

An AI investigator that works your L1 alert queue overnight and hands each
analyst a fully-evidenced case file instead of a raw alert — where every
number is reproducible, every decision is hash-chained, and the system is
structurally incapable of filing a report or contacting a customer.

---

## Open with the false positive, not the fraud

The instinct is to demo the money laundering. Resist it. Every AML vendor
demos the catch.

Demo `ALT-2026-0114` first: a $310,000 wire into a software engineer's
account, threshold rule fires, and the system scores it **2/100 and closes
it** — because the money came from a title company and left to an escrow
agent. Then show the factor list where the behavioural typologies are
explicitly discounted, with the corroborating counterparties named.

That is the demo that lands, for three reasons:

1. It is where the money is. If 90–95% of the queue is noise, the value is in
   clearing noise correctly, not in catching the one case a good analyst would
   have caught anyway.
2. It is the thing compliance leaders do not believe an AI can do. They expect
   an over-escalating machine that moves risk onto them.
3. It proves the system has judgement rather than pattern-matching. Anything
   can flag a large transaction.

Then show `ALT-2026-0117`, where the system identifies an elderly customer as
a **victim** rather than a subject, files accordingly, and refuses to contact
her — recommending the separate non-disclosing intervention pathway instead.

---

## Building the ROI with them, not for them

Do not bring a number. Bring the model and fill it in live — a number you
derived from their inputs survives procurement; a number from a vendor deck
does not.

**Inputs to ask for**

| Input | Typical question |
|---|---|
| `A` | Alerts per month reaching L1 |
| `T` | Average analyst-hours per alert (investigation + write-up) |
| `C` | Fully-loaded analyst cost per hour |
| `F` | Share of alerts closed with no SAR (the false-positive rate) |
| `B` | Current queue backlog, in days |

**The model**

```
Current annual L1 cost           = A × 12 × T × C
Cost of the false-positive share = A × 12 × T × C × F
```

The addressable line is the second one. Then apply two conservative levers,
and let *them* pick the percentages:

- **Preparation saving.** For alerts still reviewed by a human, the analyst
  starts from an evidenced case file rather than a raw alert. Realistic
  saving on `T` is a *fraction*, not elimination — say 40–60%, and let them
  argue it down.
- **Compute cost.** Metered and capped by policy. This bundle measured
  roughly $4–8 per alert on a frontier model with four sub-agents; a
  production deployment routes routine alerts to a smaller model and reserves
  the expensive path for complex cases. Subtract it explicitly — a business
  case that hides its own cost line does not survive scrutiny.

**Say out loud what you are not claiming.** You are not claiming headcount
reduction. In practice the first-year benefit lands as backlog elimination
and redeployment of senior investigators onto L2/L3 work, which is a stronger
story with a Chief Compliance Officer than a headcount number they will have
to defend to their own people.

**The benefit nobody models.** Consistency. Every alert gets the same
procedure, the same typologies considered, the same evidence standard. The
variance between your best analyst on a Monday and your newest on a Friday
disappears. That is frequently what the last examination finding was actually
about.

---

## Answering the objections you will get

**"We cannot have AI making SAR decisions."**
Agreed, and it does not. It cannot file, cannot close an alert in the system
of record, and cannot write to the case record without a human approving that
specific write. `submit_sar_draft` can only produce `pending_human_review`.
The value proposition is *preparation*, not decision.

**"How do we validate this for model risk management?"**
That question is why the architecture splits the way it does. Every number —
detector thresholds, scorecard weights, screening similarity — is
deterministic Python with fixed weights, reproducible outputs, and arithmetic
your validators can check by hand. The LLM reads those numbers and reasons
about them; it never produces them. That leaves a model-risk surface small
enough to actually validate. The 53-test regression suite pins every band, so
a weight change cannot silently move a reporting outcome.

**"What if it hallucinates a transaction?"**
Then the write is refused. `record_disposition` and `submit_sar_draft` both
verify every cited transaction id against the ledger and reject the write if
any does not exist. The narrative writer has *no data access at all* — it can
only write from the evidence pack it was handed. And the QC reviewer
independently re-derives the figures from source before anything is recorded.
Three layers, none of which is "we asked the model nicely".

**"What about tipping off?"**
Denied at the policy layer, unconditionally, and refused again at the tool
layer. Show them: ask the agent to contact the customer and let them watch it
get blocked with the statutory citation. That single moment does more than
any slide.

**"What about prompt injection from adverse media?"**
Untrusted content is confined to one sub-agent that holds no write tool, and
reading it drops that session's `integrity` label to `0`. The supervisor is
denied the media tools outright. Contamination has nowhere to land, and the
label makes it visible in the audit trail.

**"Can we prove the record was not altered?"**
Every write appends an entry carrying the SHA-256 of the entry before it.
`verify_audit_ledger` re-walks the chain. Alter or delete any historical
entry and verification fails at that index — there is a test that does exactly
that, on purpose.

**"We are not committing to one AI vendor."**
Nor should you. Omnigent is a meta-harness: the model is a config value.
Moving the QC reviewer to a different vendor for genuine cross-vendor
challenge is one line of YAML, and that is a control improvement, not just
procurement flexibility.

**"Where does our data go?"**
Nowhere you do not send it. Omnigent runs on-premise, in your own cloud, or
in your Databricks workspace. This bundle runs fully offline. The
confidentiality label is the hook for egress policy, and the credential proxy
keeps secrets out of the agent's reach entirely.

---

## The control-mapping slide

Compliance audiences buy controls, not capabilities. This table does more
work than any architecture diagram — it is reproduced in full in the README.

| Obligation | Control | Enforcement |
|---|---|---|
| No tipping off (31 USC 5318(g)(2)) | `tipping_off_control` | Runtime DENY |
| Four-eyes on case records | `four_eyes_on_case_record` | Runtime ASK |
| No automated regulatory filing | `submit_sar_draft` → `pending_human_review` only | No file operation exists |
| Evidence-based decisions | Transaction ids verified against the ledger | Write refused |
| Narrative sufficiency (five elements) | Draft validation | Write refused |
| Model risk governance | Deterministic scorecard, fixed weights | 53 pinned tests |
| Segregation of duties | Per-agent tool grants | Structural |
| Audit trail integrity | SHA-256 hash chain | `verify_audit_ledger` |
| Cost control | `cost_budget` | Runtime cap |

---

## Suggested phasing

**Phase 1 — shadow (6–8 weeks).** Point it at a copy of the alert feed. It
triages; humans triage independently; compare. This produces the agreement
statistics model risk management will require, at zero operational risk. It
also calibrates the scorecard weights against the bank's own dispositioned
history, which is the single highest-value tuning step.

**Phase 2 — assisted (3–6 months).** Analysts receive the prepared case file
and make every decision. Measure the change in time-per-alert and in
consistency. This is where the business case is actually proven.

**Phase 3 — targeted automation.** Only after Phases 1 and 2 produce evidence,
and only for the lowest-risk, highest-volume alert categories, with human
review on a sampled basis. Some institutions will never take this step, and
the first two phases still carry the investment.

Note that the same architecture extends to KYC periodic review, sanctions
alert disposition, payment dispute resolution, and credit memo preparation.
The AML queue is the beachhead, not the whole territory.

---

## What to be straight about

A demo that oversells gets found out in due diligence, and the credibility
does not come back. Say these before they ask:

- The synthetic data is designed to be tractable. Real alert queues are
  messier, and the first calibration cycle against real dispositioned history
  will move the numbers.
- Scorecard weights here are defensible defaults, not calibrated ones.
- The LLM layer needs its own model-risk validation. The deterministic layer
  is built to make that tractable; it does not remove the requirement.
- Integration is genuine work. `bankcore/store.py` is a clean seam, but
  connecting core banking, the KYC master, a screening provider, and case
  management is a project, not a configuration change.
- Nobody should deploy this to production from a demo. Phase 1 exists for a
  reason.

Saying this is not hedging. It is the thing that makes the rest of the
presentation believable to a room whose job is professional scepticism.
