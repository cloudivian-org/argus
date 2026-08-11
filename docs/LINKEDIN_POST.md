# LinkedIn post

Copy from the divider down.

---

**I gave an AI agent a bank's AML alert queue over the long weekend. The most useful thing it did was close a case.**

Singapore's National Day fell on a Sunday this year, so Monday was a holiday — and somewhere between the fireworks and the leftovers I got curious about whether the open-source agent frameworks are actually ready for regulated work. So I built something end to end and tried to break it.

The result: a financial-crime triage system on **Omnigent**, the open-source meta-harness for AI agents. One supervisor plus four specialists — a ledger investigator, a sanctions/PEP screener, a report drafter, and an independent QC reviewer — working a transaction-monitoring alert the way a Level 1 analyst does.

The demo everyone expects is the fraud catch. That's not the interesting one.

A $310,000 wire hits a software engineer's account. The rule fires. The system scores it **2 out of 100 and closes it** — because the money came from a title company and left to an escrow agent three days later. It's a house purchase. Most of what reaches an alert queue is noise, and *clearing noise correctly* is where the money is. Anything can flag a big transaction.

**The design decision that mattered:** the LLM never produces a number. Eight typology detectors and the risk scorecard are plain deterministic Python. The model reads those figures and reasons about them. That keeps the model-risk surface small enough for a validation team to actually sign off — and every figure in a report can be recomputed by hand.

**What I got wrong, and what it taught me:**

→ I blocked the agent from reading adverse media. That DENY propagated to sub-agents and disabled the very specialist meant to do the screening. The fix was better than the original: reading untrusted content lowers an integrity label, and a session carrying that label can't write to the case record. Gate the *write*, not the *read*.

→ My tamper-evident audit ledger was being written into a temp directory that died with each session. A hash chain that resets every run proves nothing. I found it only by testing end to end in the UI, not in the test suite.

→ Making the output readable roughly **doubled** the token cost. Worth every cent. The transcript *is* the deliverable — a cheap one nobody can read has no value.

→ The agent inherited my personal CLI plugins and started narrating about them inside a regulated case file.

**What it can't do, by design:** file a report, close an alert, or contact a customer. The tipping-off control is a runtime DENY citing 31 USC 5318(g)(2) — not a polite instruction. Every write to the case record pauses for human approval.

66 tests, six alert scenarios, fully synthetic data, roughly $3–9 per alert.

Not production-ready — the scorecard needs calibrating against real dispositioned history, and the LLM layer needs its own model-risk validation. But it's a working argument about *how* to build this responsibly, and I learned more from the four things that broke than from the parts that worked first time.

Everything is open: **https://github.com/cloudivian-org/argus**

---

*Disclaimer: this is a personal side project built in my own free time over the public holiday. It is not endorsed by, affiliated with, or connected to my current employer or any other company, and it does not represent their views. It was built purely to experiment with the open-source Omnigent framework and assess its effectiveness. All data is synthetic — no real customer, institution, or sanctioned party is represented, and nothing here is legal or compliance advice.*

#AI #AgenticAI #FinancialCrime #AML #Compliance #RegTech #OpenSource #SingaporeNationalDay
