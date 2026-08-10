# Argus — AML alert triage and SAR drafting on Omnigent

A working, end-to-end financial-crime use case built on
[Omnigent](https://github.com/omnigent-ai/omnigent), the open-source
meta-harness for AI agents.

**Argus** takes one transaction-monitoring alert and works it the way a Level 1
FIU analyst does: it reads the alert and the customer's KYC profile, runs a
deterministic typology analysis over the ledger, screens the whole counterparty
network against sanctions and PEP lists, sweeps adverse media, scores the alert
on a fixed scorecard, drafts a SAR narrative where one is warranted, has that
draft independently challenged, and records an auditable disposition.

It recommends. **A human decides.** Nothing here files a report, closes an
alert, or contacts a customer.

The bundle runs offline against a synthetic bank. No real customer data, no
real sanctions list, no network calls.

```bash
omnigent run . -p "Triage ALT-2026-0113"
```

---

## Why this use case

AML alert triage is the highest-volume, lowest-leverage work in a bank's
financial crime function, and the economics are brutal in a way that is easy
to verify with any compliance leader:

- Transaction-monitoring rules are tuned for recall, not precision. Industry
  false-positive rates on L1 alert queues sit in the **90–95%** range.
- Every alert still has to be worked, evidenced, and documented, because the
  regulator's question is never "did you catch it" but "can you show me how you
  decided".
- The scarce resource is **investigator hours**, and the majority of them are
  spent proving that nothing happened.
- The failure mode is asymmetric. Under-report and you get an enforcement
  action. Over-report and you bury the genuine reports in volume — which is
  itself a finding.

That makes it near-ideal for an agent system, *provided* the system is built so
its output is auditable. An AI that produces a confident narrative nobody can
trace is worse than no AI at all. This bundle is an argument about how to build
that responsibly, not just a demo that it can be done.

---

## What the demo actually shows

Six alerts across six typologies, with one deliberately built to be a **false
positive**. The scorecard is deterministic, so these numbers are reproducible
on any machine:

| Alert | Rule | Customer | Score | Band | Recommended |
|---|---|---|---|---:|---|
| `ALT-2026-0113` | STRUCT-01 | Marcus Delgado (retail SME) | 72 | high | `escalate_l2` |
| `ALT-2026-0114` | THRESH-01 | Priya Raman (salaried) | **2** | low | **`close_no_sar`** |
| `ALT-2026-0115` | HRJ-02 | Meridian Polymer Trading LLC | 99 | critical | `recommend_sar` |
| `ALT-2026-0116` | PASSTHRU-05 | Aiden Okafor (student) | 79 | high | `escalate_l2` |
| `ALT-2026-0117` | VULN-03 | Eleanor Whitfield (age 78) | 86 | critical | `recommend_sar` |
| `ALT-2026-0118` | LAYER-07 | Novaterra Holdings Ltd | 100 | critical | `recommend_sar` |

**`ALT-2026-0114` is the one to demo first.** A $310,000 wire lands on a
software engineer's account whose declared monthly turnover is $18,000, and the
threshold rule fires. It is a house purchase: the money arrives from a title
company and leaves to an escrow agent three days later. The system scores it
**2** and closes it. Correctly clearing a false positive is the entire business
case; escalating everything is not caution, it is cost.

`ALT-2026-0117` is the second one to demo. An elderly customer breaks a
certificate of deposit at a penalty and wires $184,000 to Ghana and a crypto
exchange over ten weeks. The system files a report **and identifies the
customer as a victim, not a perpetrator** — which changes the subject, the
activity type, and the follow-up action. It also refuses to contact her, and
recommends the separate non-disclosing intervention pathway instead.

---

## How it uses Omnigent

This is not a Python script with an LLM call in it. Every structural piece is an
Omnigent primitive, which is what makes the governance real rather than
prompt-deep.

| Omnigent primitive | Used for |
|---|---|
| **Agent bundle** (`config.yaml` + `agents/` + `skills/` + `tools/`) | The whole system is one directory. `omnigent run .` is the entire deployment step. |
| **Sub-agents** (`tools.agents`) | Four specialists — investigator, screening analyst, narrative writer, QC reviewer — each a separate session with its own context and its own tool grant. |
| **Per-agent local tools** (`tools/python/*.py`) | Least privilege is expressed structurally: an agent simply does not have the tool it should not call. `narrative_writer` has **zero** tools. |
| **Guardrail policies** (`guardrails.policies`) | The tipping-off DENY, the maker-checker ASK, the untrusted-content write gate, the fan-out bound, the purpose gate, and the spend cap. Enforced by the runtime, not by asking the model nicely — and they apply to every sub-agent session in the tree. |
| **Information-flow labels** (`guardrails.labels`) | `confidentiality` rises when customer data is read; `integrity` falls when untrusted media is read. Contamination becomes a visible, machine-readable session property. |
| **Skills** (`skills/*/SKILL.md`) | The triage procedure, the narrative standard, and the typology red-flag library — versioned as documents a compliance officer can review and edit without touching code. |
| **`ask_timeout`** | 86,400s, so a maker-checker approval survives a reviewer stepping away from the desk. |
| **Harness independence** | Every agent declares `harness: claude-sdk`, but the QC reviewer is designed to be moved to a different vendor (`codex`, `cursor`, `hermes`) for genuine cross-vendor challenge. One line of YAML. |

The harness-independence point is the strategic one for a bank. Model
procurement, model risk management, and vendor concentration risk are all live
concerns in this domain. Omnigent means the choice of model is a config value,
not an architecture.

---

## Architecture

```
                          ┌──────────────────────────────┐
   alert id ────────────▶ │  ARGUS  (supervisor)         │
                          │  owns the case & the decision│
                          │  no shell, no filesystem     │
                          └───┬───────────────┬──────────┘
                              │ parallel      │
              ┌───────────────┘               └────────────────┐
              ▼                                                ▼
   ┌────────────────────────┐                    ┌──────────────────────────┐
   │ financial_investigator │                    │   screening_analyst      │
   │ ledger + 8 detectors   │                    │   sanctions / PEP / media│
   │ read-only              │                    │   taints integrity label │
   └───────────┬────────────┘                    └────────────┬─────────────┘
               │             evidence pack + screening pack   │
               └──────────────────────┬───────────────────────┘
                                      ▼
                          ┌──────────────────────────────┐
                          │  score_alert_risk            │  deterministic
                          │  fixed weights, capped       │  scorecard
                          └──────────────┬───────────────┘
                                         ▼
                    ┌────────────────────────────────────────┐
                    │ narrative_writer   (NO data access)    │
                    │ writes only from the packs it is given │
                    └────────────────────┬───────────────────┘
                                         ▼
                    ┌────────────────────────────────────────┐
                    │ qc_reviewer  (read-only, adversarial)  │
                    │ re-derives every figure from source    │
                    └────────────────────┬───────────────────┘
                                         ▼
                    ┌────────────────────────────────────────┐
                    │ submit_sar_draft / record_disposition  │
                    │        ⟵ HUMAN APPROVAL REQUIRED ⟶     │
                    │  hash-chained audit ledger             │
                    └────────────────────────────────────────┘
```

Two design choices are worth calling out, because they are the difference
between a demo and something a bank could actually deploy.

**The narrative writer has no data access at all.** It can only write from the
evidence pack it is handed. A drafter that could go look things up could also
go invent them; removing the capability removes the failure mode. Every
sentence in a draft is therefore traceable to material already gathered and
recorded.

**Numbers come from Python, not from the model.** The eight typology detectors
and the scorecard are ordinary deterministic code. The model reads their output
and reasons about it. This keeps the model-risk surface small enough to
actually validate, and it means every figure in a filing can be recomputed by
hand.

---

## Repository layout

```
.
├── config.yaml                 # Argus — the supervisor agent
├── agents/
│   ├── financial_investigator/ # ledger analysis + typology detectors
│   ├── screening_analyst/      # sanctions / PEP / adverse media (+ integrity taint)
│   ├── narrative_writer/       # SAR drafting — deliberately no tools
│   └── qc_reviewer/            # independent adversarial challenge
├── skills/
│   ├── alert-triage/           # the triage procedure and evidence standard
│   ├── sar-narrative/          # narrative structure, house style, worked openings
│   └── typology-library/       # red flags, and what argues each finding down
├── tools/python/               # 11 governed banking tools (Argus's grant)
├── bankcore/                   # the deterministic layer
│   ├── store.py                #   read-only data access (the integration seam)
│   ├── typologies.py           #   8 AML detectors
│   ├── screening.py            #   explainable fuzzy name matching
│   ├── scoring.py              #   the risk scorecard
│   ├── casefile.py             #   hash-chained tamper-evident audit ledger
│   └── api.py                  #   shared tool bodies
├── data/                       # synthetic bank sandbox (generated)
├── casefiles/                  # case files + audit_ledger.jsonl (written at runtime)
├── scripts/generate_data.py    # regenerates the sandbox deterministically
└── tests/test_argus.py         # 54 regression tests
```

---

## Install and run

### 1. Install Omnigent

```bash
curl -fsSL https://raw.githubusercontent.com/omnigent-ai/omnigent/main/scripts/install_oss.sh | sh
```

Or manually (needs Python 3.12+):

```bash
uv tool install --python 3.12 omnigent
```

### 2. Configure a model

```bash
omnigent setup
```

This bundle was built and tested against a **Claude subscription via the
`claude` CLI**. An `ANTHROPIC_API_KEY`, an OpenAI-compatible gateway, or a
Databricks workspace all work equally well — no agent in the bundle pins a
model.

### 3. Generate the sandbox

```bash
python3 scripts/generate_data.py
```

Deterministic (fixed seed, as-of date 2026-08-01), so the figures in this
README reproduce exactly.

### 4. Run a triage

```bash
# Start with the false positive — it is the most convincing one.
omnigent run . -p "Triage ALT-2026-0114"

# The structuring case.
omnigent run . -p "Triage ALT-2026-0113"

# The victim case — watch it refuse to contact the customer.
omnigent run . -p "Triage ALT-2026-0117"

# See the queue first.
omnigent run . -p "Show me the alert queue, then triage the highest-priority one."
```

**Run this interactively.** When Argus reaches `record_disposition` or
`submit_sar_draft`, the maker-checker policy pauses and asks you to approve.
That pause *is* the control — it needs a human at the keyboard.

For the browser or a phone:

```bash
omnigent start          # then open the printed URL, New Chat, pick this agent
```

### 5. Verify the audit trail

```bash
cat casefiles/ALT-2026-0113.json          # the case file
cat casefiles/audit_ledger.jsonl          # the hash chain
omnigent run . -p "Verify the audit ledger"
```

---

## The control surface

This is the part to walk a compliance officer through. Each control is
mechanism, not prompt text — the model cannot reason its way past any of them.

| Control | How it is enforced | What it prevents |
|---|---|---|
| **Tipping-off** | `guardrails.policies.tipping_off_control` — unconditional DENY on `contact_customer` | Disclosure of an investigation to its subject — a criminal offence under 31 USC 5318(g)(2) |
| **Maker-checker** | `four_eyes_on_case_record` — ASK on `record_disposition` and `submit_sar_draft` | Any AI-authored record entering the case file unreviewed |
| **No filing authority** | `submit_sar_draft` can only produce `pending_human_review`; there is no file operation | An AI system filing a regulatory report |
| **Evidence citation** | `record_disposition` rejects a disposition with no cited transactions, or with ids that do not exist | Conclusions resting on invented evidence |
| **Narrative sufficiency** | `submit_sar_draft` rejects drafts under 900 chars, missing any of the five elements, containing hedging language, or whose total does not reconcile to the cited entries within 10% | Fluent but deficient filings |
| **Scorecard discipline** | A disposition departing from the scorecard band is refused until a written reason is supplied | Silent overrides of the bank's own risk model |
| **Separation of duties** | Only the supervisor holds write tools; the drafter has no data access; the reviewer is read-only | The agent that writes the narrative marking its own homework |
| **Untrusted content isolation** | Reading adverse media drops the session's `integrity` label to `0`, and `no_case_record_after_untrusted_content` then DENIES `record_disposition` and `submit_sar_draft` in that session | Prompt injection from third-party content steering a disposition or a filing |
| **Data confidentiality** | Reading customer data raises `confidentiality` to `1` for the session | Untracked PII flow; the label is the hook a real deployment gates egress on |
| **No shell, no filesystem** | Argus declares no `os_env` block | A generic escape hatch that would have to be audited separately |
| **Tamper-evident audit** | Every write appends a SHA-256-chained ledger entry; `verify_audit_ledger` re-walks the chain | Silent alteration of the record after the fact |
| **Spend cap** | `cost_budget` — $20.00 hard cap per session, ASK at $12.00 | Unit economics that are aspirational rather than enforced |
| **Fan-out bound** | `spawn_bounds` — max 4 dispatches per turn | Runaway recursive delegation |

### What this system cannot do, by design

- File a SAR.
- Close an alert in the bank's system of record.
- Contact a customer.
- Write to the case record without a human approving that specific write.
- Modify a customer record or a ledger entry — `bankcore/store.py` is read-only.
- Alter its own audit history without the hash chain reporting it.

---

## How it was built

Roughly the order the work happened in, because the order matters:

1. **Read the Omnigent spec surface first.** `docs/AGENT_YAML_SPEC.md`,
   `docs/POLICIES.md`, and the shipped `examples/sentinel` and `examples/polly`
   bundles, which are the most current expression of the schema. Sentinel in
   particular is the template for a read-only, policy-constrained orchestrator.
2. **Built the synthetic bank before anything else.** `scripts/generate_data.py`
   hand-authors six scenarios — structuring, an explained house purchase, trade
   -based laundering with a sanctions nexus, a mule funnel account, elder
   exploitation, and PEP layering — inside 12 months of ordinary baseline
   traffic, so the suspicious activity has to be found rather than merely
   spotted in an empty ledger. 1,007 transactions, 6 customers, 8 accounts.
3. **Built the deterministic layer next, before any agent existed.** Eight
   detectors, an explainable fuzzy screening matcher, the scorecard, and the
   hash-chained ledger. The discipline here is deliberate: if the model can
   produce a number, the number cannot be validated.
4. **Tuned the scorecard until it discriminated.** The first version saturated —
   four of six alerts scored 100, which is a scorecard that has stopped ranking
   anything. Fixed with per-category ceilings and an "explained activity"
   discount that damps the behavioural typologies when large movements settle
   against regulated, purpose-identifying counterparties. That is also what
   drives `ALT-2026-0114` to 0. Final spread: 2 / 72 / 79 / 86 / 99 / 100.
5. **Wrapped the deterministic layer in 11 governed tools**, with the write
   tools carrying their own refusal logic rather than trusting the caller.
6. **Wrote the agents.** One supervisor, four specialists, with tool grants
   assigned per agent so least privilege is structural.
7. **Added the governance layer** — six policies and two information-flow
   labels on the supervisor, plus the media taint on the screening analyst.
8. **Wrote the skills** as the documents a compliance function would own.
9. **Tested it**, which is the next section.

### The integration seam

`bankcore/store.py` is the only module that knows where data comes from. In a
real deployment you replace its loaders with calls to the core banking
platform, the KYC master, the sanctions screening provider, and the case
management system. Nothing above that file changes. Tool signatures, agent
prompts, policies, and skills are all portable.

Realistic first integrations: Fiserv / FIS / Temenos for core, NICE Actimize or
Oracle Mantas for the alert feed, Dow Jones / LSEG / ComplyAdvantage for
screening, and the bank's own case management for disposition write-back.

---

## How it was tested

### Deterministic regression suite — 54 tests

```bash
python3 -m unittest discover -s tests -t . -v
```

```
Ran 54 tests in 1.069s

OK
```

The suite protects two different things.

**The deterministic layer**, because detector thresholds and scorecard weights
are exactly what a model-risk function has to validate and sign off. If a
weight moves, a band moves, and a band moving silently changes what gets
reported to a financial intelligence unit. So the expected band for all six
scenarios is pinned, along with a test that the scores have not re-saturated
and a test that the false positive stays at least 40 points below every true
positive.

**The control surface**, because a control that is not tested is a control that
is merely asserted:

| Test class | Covers |
|---|---|
| `SandboxIntegrity` | Referential integrity of the synthetic dataset |
| `Detectors` | Each scenario triggers the typology it was built for, and the false positive does not trigger structuring |
| `Screening` | `FZE`→`FZCO` variant matches; unrelated names stay clear; shared corporate suffixes alone never collide |
| `Scorecard` | All six bands pinned; discrimination preserved; scores reproducible; every factor carries a stated basis |
| `LedgerIntegrity` | The chain verifies when untouched, and **fails** when an entry is altered or deleted |
| `DispositionControls` | Thin rationale, uncited evidence, fabricated transaction ids, and unexplained scorecard departures are all rejected |
| `SarDraftControls` | Short narrative, missing element, hedging language, fabricated ids, and non-reconciling totals are all rejected; an accepted draft is never marked filed |
| `TippingOffControl` | Customer contact fails closed at the tool layer as well as at the policy layer |
| `BundleWiring` | The Omnigent spec loads with all six policies, both labels, four sub-agents, and three skills attached — and asserts that the drafter has no tools, that no sub-agent holds a write tool, that only the screening analyst can read media, and that the supervisor declares no shell access |

That last class is the one that matters most for a proposal. It tests the
*claims* — every governance property in the table above is asserted against the
spec Omnigent actually loads, so the architecture diagram cannot quietly drift
away from reality.

### What the live runs changed

The deterministic suite passes without ever starting a model. Running the
thing for real against Omnigent found four defects the suite could not have,
and each one is worth recording because they are the failure modes anyone
building on this stack will hit.

1. **Sub-agent tool files resolve against the bundle root.** Omnigent loads a
   sub-agent's tool file as `workdir / info.path`, where `workdir` is the
   *bundle* root — not the sub-agent's directory. A tool file that existed
   only under `agents/screening_analyst/tools/python/` was declared in that
   agent's grant but could not be loaded, and the sub-agent died on a missing
   file. Fix: every tool file also exists at the bundle root. The per-agent
   directory still defines the *grant*, which is the control that matters.

2. **Guardrail policies propagate to every sub-agent session.** After fix 1,
   the screening tools were necessarily in the supervisor's discovery scope,
   so a blanket DENY was added to keep them out of the deciding session. That
   DENY then propagated down and blocked `screening_analyst` — the one agent
   that is supposed to do the screening. The whole screening step failed, and
   the supervisor fell back to the scorecard's built-in screening. Fix:
   **gate the write on the label instead of banning the read.** Reading media
   drops `integrity` to `0`; a session at `integrity: 0` is denied
   `record_disposition` and `submit_sar_draft`. Media retrieval is therefore
   only *useful* inside the sub-agent that holds no write tool, which forces
   the delegation without disabling anything.

3. **The spend cap was set below the cost of the work.** `cost_budget` was
   $5.00 with an ASK at $2.50; a real triage crossed the warning mid-run and,
   in a non-interactive session, the ASK failed closed and ended the run.
   Correct behaviour for a control, wrong number. Raised to a $20.00 cap with
   the warning at $12.00, based on measured cost.

4. **The scorecard contradicted its own tooling on KYC staleness.**
   `get_customer_profile` reported a review 417 days old as stale while the
   scorecard's mitigant treated it as current, because the mitigant compared
   against a hardcoded date instead of ageing the review. The agent noticed
   the discrepancy in its own reasoning and flagged it. Fix: age the review
   against the as-of date. Two scores moved (2 and 86); no band changed.

Defect 2 is the interesting one. The instinct — remove the capability — was
wrong in a way that only showed up under execution, and the correct control
turned out to be strictly better: it is an information-flow property rather
than a tool ban, so it holds no matter which agent reads what.

One further observation, not a defect: a `Sub-agent 'narrative_writer' did not
resolve in the parent spec; falling back to the parent spec` warning appears
in the runner log. It is benign — it fires when a session's spec cache already
holds the child spec and that spec is searched for its own name. Verified
directly: the drafter session runs as `narrative_writer` with zero tools. Worth
knowing, because that same warning *would* be serious if the name genuinely did
not resolve — the documented fallback runs the child as a clone of the parent,
with the parent's tools.

### Live end-to-end runs

Run against Claude via the `claude` CLI, on `ALT-2026-0114` (the false
positive) and `ALT-2026-0113` (structuring), exercising the full path:
supervisor → parallel sub-agent fan-out → scorecard → narrative → QC challenge
→ maker-checker approval prompt → hash-chained ledger write.

Reproduce with:

```bash
python3 scripts/generate_data.py
python3 -m unittest discover -s tests -t .
omnigent run . -p "Triage ALT-2026-0114"
```

---

## Taking this to production

What this bundle is: a complete, working, honestly-governed reference
implementation on a synthetic bank.

What it is not: a validated production system. Getting there is real work, and
being straight about it is worth more in a customer conversation than pretending
otherwise.

1. **Model risk management.** The deterministic layer is designed to be
   validated — fixed weights, reproducible outputs, hand-checkable arithmetic.
   The LLM layer needs its own validation: benchmark against historically
   dispositioned alerts, measure agreement with senior investigators, and
   establish the challenger process.
2. **Tune against real alert volume.** The scorecard weights here are
   defensible defaults, not calibrated ones. Calibration is done against the
   bank's own dispositioned history.
3. **Human-in-the-loop stays.** For at least the first phase, every disposition
   is reviewed. The value is in the *preparation* — the analyst arrives at a
   fully-evidenced case file instead of a raw alert.
4. **Data residency and privacy.** Omnigent runs on-premise, in the bank's own
   cloud, or in a Databricks workspace. The confidentiality label is the hook
   for egress policy; the credential proxy keeps secrets out of the agent's
   reach entirely.
5. **Cross-vendor QC.** Move `qc_reviewer` to a different model vendor so the
   challenge does not share the author's blind spots. One line of YAML.
6. **Extend the pattern.** The same architecture — deterministic analytics,
   specialist sub-agents, policy-enforced separation of duties, tamper-evident
   audit — carries directly to KYC periodic review, sanctions alert
   disposition, payment dispute resolution, and credit memo preparation.

---

## Data and legal notes

Every record in `data/` is **fabricated**. The customers, transactions,
counterparties, news articles, and watchlist entries are invented. The
"sanctions" entries imitate the *shape* of OFAC/UN/EU and PEP records so the
screening logic has something realistic to match against; they name no real
designated person or entity, and every one is marked `(simulated record)`.

Regulatory references (31 USC 5324, 31 CFR 1010.313, 31 USC 5318(g)(2), FinCEN
advisories, FATF Recommendations) are cited to show how findings map to
obligations. They are illustrative, not legal advice. Any real deployment needs
review by the institution's own compliance and legal functions against its own
jurisdiction.

---

## Licence

Apache 2.0, matching Omnigent.

Built on [Omnigent](https://github.com/omnigent-ai/omnigent) — the open-source
meta-harness for AI agents.
