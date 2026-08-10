---
name: typology-library
description: >-
  Red-flag reference for the AML typologies this system detects — what each
  pattern looks like, what argues against it, and what a filing has to say
  about it. Load when interpreting detector output.
---

# Typology reference

Each detector answers a narrow question. This is how to read its answer,
and — the part analysts skip — what would argue the finding down.

---

## Structuring

**Pattern.** Cash deposits deliberately kept below the currency transaction
reporting threshold ($10,000 in the US) so no report is generated. Split
across days, across branches, sometimes across related parties.

**Confirms it.** Amounts clustering in a narrow band just under the
threshold. Multiple branches for one account. Deposits on consecutive
business days. Near-total absence of any deposit *above* the threshold in a
business that plainly generates that much cash. Rapid onward sweep after
each cluster.

**Argues against it.** A genuinely cash-intensive business whose daily takings
naturally land in that range. Irregular, non-clustered amounts. Deposits
above the threshold present in the same period — someone evading the report
does not file one voluntarily. Deposit sizes tracking a documented business
cycle.

**Say in the filing.** The count, the band, the span, the branch spread, and
explicitly that no deposit reached the threshold. Contrast against the
declared turnover.

**Reference.** 31 USC 5324; 31 CFR 1010.313; FATF R.10, R.20.

---

## Funnel / pass-through (money mule)

**Pattern.** Many small credits from unrelated senders, moved out almost
immediately — ATM cash, a virtual-asset venue, or an onward transfer.
The account is a conduit, not a store of value.

**Confirms it.** A high pass-through ratio (>0.8). Many distinct senders
with no plausible relationship to the account holder. Same-day or next-day
outflow. A recently opened account. Turnover wildly beyond the holder's
declared means — students, the newly employed, and the recently arrived are
the recruitment pool.

**Argues against it.** A documented reason to receive many small payments:
a tutoring business, a rideshare driver, an event organiser, a fundraiser.
Senders who repeat, indicating an ongoing relationship. Funds that
actually sit in the account.

**Say in the filing.** Sender count, inbound total, pass-through ratio,
the outflow mix, account age, and the gap against declared income. Whether
the holder appears to be a knowing participant or a recruited victim —
these are different reports.

**Reference.** FinCEN FIN-2020-A008; FATF R.10, R.15.

---

## Trade-based money laundering

**Pattern.** Value moved under cover of trade. Over- or under-invoicing,
phantom shipments, or a corridor that has nothing to do with the declared
business.

**Confirms it.** Exactly round-value wires — real invoices carry cents,
freight adjustments, and partial settlements. Counterparties outside the
declared trade corridors. Goods descriptions that do not match the customer's
industry. Payment terms inconsistent with the trade. Free-zone or
transhipment counterparties with no apparent role.

**Argues against it.** Documented invoices reconciling to the payments.
Shipping documents matching the goods and the route. A corridor the customer
disclosed and can explain. Amounts carrying the irregularity of genuine
commerce.

**Say in the filing.** The exact amounts and their roundness, the
counterparties and jurisdictions, the mismatch against declared corridors,
and what documentation was requested and whether it was produced.

**Reference.** FATF *Trade-Based Money Laundering* (2020); FinCEN
FIN-2010-A001.

---

## Layering through related entities

**Pattern.** Funds received and forwarded within a day or two to related
parties, in near-matching amounts, with no economic purpose the flow itself
reveals. Often through corporate structures across several jurisdictions.

**Confirms it.** In/out matching above ~90% of value. Holding periods under
48 hours. Onward counterparties sharing ownership, address, or directors.
Round or near-round amounts. Narrative descriptions that assert a purpose
("consultancy", "advisory") without any deliverable evidenced. PEP control.

**Argues against it.** A genuine treasury function with documented
intercompany agreements. Retained margin consistent with a real commercial
role. A group structure disclosed at onboarding and consistent with the
flows.

**Say in the filing.** Each matched pair, the holding period, the retained
percentage, the relationships between the entities, and the absence of
evidenced economic purpose.

**Reference.** FATF R.10, R.12; Wolfsberg Correspondent Banking Principles.

---

## PEP-related corruption exposure

**Pattern.** A politically exposed person, or their close associates,
receiving value plausibly connected to their public function.

**Confirms it.** Payments from entities in the PEP's former area of
responsibility. Consultancy or advisory fees with no evidenced deliverable.
Ownership through nominees or secrecy jurisdictions. Source of wealth
documentation that was promised and never delivered. Adverse media on the
public role.

**Argues against it.** Evidenced pre-existing wealth. An arm's-length
commercial relationship unrelated to the public function. Complete,
independently verified source-of-wealth documentation.

**Say in the filing.** The PEP's role and dates, the ownership chain, the
payer's connection to the public function, the payments, and specifically
what source-of-wealth evidence was requested, what arrived, and what did not.

**Reference.** FATF R.12; 31 CFR 1010.620.

---

## Elder financial exploitation

**Pattern.** An older or vulnerable customer's assets moved out under
another party's influence — romance fraud, an advance-fee scheme,
impersonation, or coercion by someone close to them.

**Confirms it.** An abrupt break from a long, stable history. Early
redemption of a term deposit at a penalty — a strong indicator, because it
means someone is prioritising urgency over their own money. Serial transfers
to one overseas corridor. Escalating amounts and escalating pretexts
("customs fee", "legal fee", "final fee"). A beneficiary the customer has
never met. Reluctance or agitation when branch staff ask the purpose.
Coaching, or a third party present during transactions.

**Argues against it.** A documented, verifiable relationship. Activity
consistent with a plan the customer described in advance. Genuine
independent legal or financial advice on file.

**Say in the filing.** The baseline and the break. The chronology of transfers
with the stated pretexts. Beneficiary details and jurisdiction. Any branch
observation of demeanour, quoted as observation. And **state that the
customer appears to be a victim** — this changes the subject of the report
and the follow-up entirely.

**Careful.** The customer is not the wrongdoer. The report is still filed —
and the customer is still not told about it. Intervention, where warranted,
is a separate human-run process designed not to disclose the report. Never
combine the two.

**Reference.** FinCEN FIN-2022-A002; FATF R.10.

---

## Profile deviation and behavioural break

**Pattern.** Activity that no longer matches what the bank was told to
expect, or that abruptly departs from the customer's own long-run baseline.

**Confirms it.** Turnover multiples above declared expectations. New
jurisdictions never previously seen. A dormant account reactivating into
high-value flow. Channel mix shifting toward cash or virtual assets.

**Argues against it.** A life event that explains it — a property purchase,
an inheritance, a business sale, a bonus — where the counterparties
corroborate the explanation. A regulated, purpose-identifying counterparty
(a title company, an escrow agent, a payroll processor) is strong
corroboration, because that counterparty ran its own diligence.

**Say in the filing.** Declared expectation, observed activity, the multiple,
and what the customer's declared source of funds was — then why it does not
account for the gap.

**Reference.** FATF R.10; 31 CFR 1020.210(a)(2)(v).

---

## Reading a multi-typology case

Typologies rarely appear alone, and the combination usually names the scheme
better than any single detector:

- structuring + rapid outward sweep → cash placement
- funnel + virtual-asset off-ramp → mule network cash-out
- round-value wires + non-declared corridor + sanctions near-match →
  trade-based laundering with a possible sanctions nexus
- rapid in-out + PEP control + shell counterparties → corruption layering
- behavioural break + vulnerable customer + single overseas corridor →
  elder exploitation

Name the scheme, then evidence each component. A filing that lists detectors
without assembling them into an account of what happened makes the reader do
the work you were supposed to do.
