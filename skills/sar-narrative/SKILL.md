---
name: sar-narrative
description: >-
  How to structure a filable suspicious activity report narrative — the five
  required elements, the house style, the validation the submission tool
  enforces, and worked openings. Load before drafting or reviewing narrative.
---

# SAR narrative standard

## The reader

A law-enforcement analyst opening this cold, with no context, possibly two
years from now, who cannot ask you anything. If it is not on the page, it is
lost. Most deficient narratives are not wrong — they are written for someone
who already knows the case.

## Structure

1. **Summary paragraph.** Who, what conduct, over what period, for how much.
   One paragraph. An analyst triaging a queue reads this and nothing else.
2. **Customer background.** Relationship tenure, product set, occupation or
   industry, declared source of funds, expected activity, KYC currency.
   This is what makes the anomaly legible.
3. **The activity, chronologically.** Dates, amounts, channels,
   counterparties, jurisdictions, branches. In order. Narrative prose, not a
   table dump.
4. **Why it is suspicious.** The analysis. What was expected, what happened,
   the gap, what was ruled out, what documentation was sought and whether it
   arrived. This paragraph carries the filing.
5. **Bank action.** Account status, monitoring applied, restrictions,
   referrals, whether this is a continuing-activity report.

## The five elements

`submit_sar_draft` will reject a draft that does not claim all five.

- **Who** — full names, roles, relationship to the account, identifiers.
- **What** — instruments, channels, amounts, and the conduct.
- **When** — the date range, and the chronology inside it.
- **Where** — accounts, branches, channels, jurisdictions.
- **Why** — why this is suspicious *for this customer*.

## House style

**Do**

- Plain declarative English, third person, past tense for the activity.
- Exact figures and dates, as the detectors reported them.
- Describe the pattern; do not just name it.
- State what was ruled out, and how.
- Attribute media allegations to the outlet and summarise them.
- Say plainly where the subject appears to be a victim.

**Do not**

- Hedge. "Might be", "could possibly", "seems", "I think", "probably just" —
  `submit_sar_draft` scans for these and rejects the draft. They read to a
  regulator as an admission that the analysis was not done.
- Round beyond the given precision, or state a total you did not see computed.
- Use internal system names, rule codes, queue names, or model/vendor names.
- Quote adverse media verbatim.
- Speculate about intent beyond what the transactions support.
- Mention how the draft was produced.

## Naming the pattern is not describing it

> Structuring activity was observed on the account.

Tells the reader nothing. Compare:

> Between 14 July and 29 July 2026, the customer made fourteen cash deposits
> to account ACC-2007-01 totalling $128,600. Each deposit fell between $8,400
> and $9,900 — below the $10,000 currency transaction reporting threshold —
> and no single deposit reached that threshold. The deposits were made across
> three branches (BR-014, BR-027, BR-041), and funds were swept to a personal
> savings account in four transfers within days of each cluster.

Same finding. The second one can be acted on.

## Worked openings

**Structuring.**

> This report concerns Marcus Delgado, the owner of a convenience store and a
> business banking customer since 17 February 2011, who between 14 July and
> 29 July 2026 deposited $128,600 in cash to his business account in fourteen
> separate transactions, each below the $10,000 currency transaction
> reporting threshold, across three branches.

**Trade-based laundering.**

> This report concerns Meridian Polymer Trading LLC, a wholesale industrial
> chemicals business, which between 4 June and 9 July 2026 sent six wire
> transfers of exactly $250,000 each, totalling $1,500,000, to two
> counterparties in the United Arab Emirates and Kazakhstan — neither within
> the trade corridors the customer declared at onboarding, and one of which
> is a close name match to an entity on a sanctions list.

**Elder exploitation.**

> This report concerns activity on the account of Eleanor Whitfield, aged 78,
> a retail customer since 9 February 2004, who between 22 May and 26 July
> 2026 transferred $184,000 to beneficiaries in Ghana and to a virtual-asset
> exchange, funded in part by the early redemption of a certificate of
> deposit at a penalty. The pattern is consistent with the customer being the
> victim of a romance or advance-fee fraud rather than a knowing participant.

## What the submission tool enforces

`submit_sar_draft` rejects a draft that:

- runs under 900 characters (too short to cover five elements);
- does not claim all five elements;
- contains hedging language;
- names no subject;
- cites transaction ids that do not exist on the customer's accounts;
- cites no transactions at all;
- reports a total more than 10% away from the sum of the cited entries.

These are cheap mechanical checks catching the deficiencies that show up most
often in real filings. Passing them is the floor, not the standard.

## What submission does not do

It does not file anything. The draft is parked in `pending_human_review` and
the fact is written to the audit ledger. The filing decision, and the
submission to the financial intelligence unit, stay with a qualified human in
the bank's own reporting system.
