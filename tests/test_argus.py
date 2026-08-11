"""Regression suite for the Argus AML triage bundle.

Two things are being protected here.

The first is the deterministic layer. Detector thresholds, scorecard
weights, and screening similarity are the parts of this system that a
model-risk function has to validate and sign off. If a weight moves, a
band moves, and a band moving silently changes what gets reported to a
financial intelligence unit. So the expected band for every scenario is
pinned.

The second is the control surface. The refusals — tipping-off, evidence
citation, hedging language, ledger integrity — are the claims this system
makes to a regulator. A control that is not tested is a control that is
asserted.

Run:  python3 -m unittest discover -s tests -v
      (or: python3 tests/test_argus.py)
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bankcore import casefile, scoring, screening, store, typologies  # noqa: E402


try:  # The @tool decorator lives in the Omnigent client package.
    import omnigent_client  # noqa: F401

    HAS_OMNIGENT_CLIENT = True
except ImportError:  # pragma: no cover - depends on which interpreter runs
    HAS_OMNIGENT_CLIENT = False

# Loading a tool module executes `from omnigent_client.tools import tool`, so
# these tests need the interpreter Omnigent was installed under. Skipping with
# a clear reason beats 39 identical ImportError tracebacks for someone running
# the suite on the system python.
needs_client = unittest.skipUnless(
    HAS_OMNIGENT_CLIENT,
    "omnigent_client not importable — run with the interpreter Omnigent is "
    "installed under, e.g. ~/.local/share/uv/tools/omnigent/bin/python, "
    "or use ./scripts/demo.sh which finds it for you",
)


def load_tool(name: str, agent: str | None = None):
    """Import a tool module the way the Omnigent runner does — by path."""
    base = ROOT / "tools" / "python" if agent is None else ROOT / "agents" / agent / "tools" / "python"
    spec = importlib.util.spec_from_file_location(f"_tool_{agent or 'root'}_{name}", base / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, name)


class SandboxIntegrity(unittest.TestCase):
    """The synthetic dataset must be internally consistent."""

    def test_alerts_reference_real_customers_and_accounts(self):
        customer_ids = {c["customer_id"] for c in store.customers()}
        account_ids = {a["account_id"] for a in store.accounts()}
        for alert in store.alerts():
            self.assertIn(alert["customer_id"], customer_ids, alert["alert_id"])
            for account_id in alert["account_ids"]:
                self.assertIn(account_id, account_ids, alert["alert_id"])

    def test_transactions_belong_to_real_accounts(self):
        account_ids = {a["account_id"] for a in store.accounts()}
        for txn in store.transactions():
            self.assertIn(txn["account_id"], account_ids, txn["txn_id"])

    def test_transaction_ids_are_unique(self):
        ids = [t["txn_id"] for t in store.transactions()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_dataset_is_non_trivial(self):
        self.assertGreater(len(store.transactions()), 500)
        self.assertEqual(len(store.alerts()), 6)


class Detectors(unittest.TestCase):
    """Each scenario must trigger the typology it was built to represent."""

    def test_structuring_fires_on_the_cash_scenario(self):
        finding = typologies.structuring("CUS-1007", 90)
        self.assertTrue(finding["triggered"])
        self.assertEqual(finding["confidence"], "high")
        metrics = finding["metrics"]
        self.assertEqual(metrics["below_threshold_deposit_count"], 14)
        self.assertEqual(metrics["at_or_above_threshold_deposit_count"], 0)
        self.assertEqual(len(metrics["distinct_branches"]), 3)
        self.assertAlmostEqual(metrics["total_below_threshold_usd"], 129700.0, places=2)

    def test_structuring_does_not_fire_on_a_salaried_customer(self):
        self.assertFalse(typologies.structuring("CUS-1002", 90)["triggered"])

    def test_pass_through_fires_on_the_mule_scenario(self):
        finding = typologies.pass_through("CUS-1031", 90)
        self.assertTrue(finding["triggered"])
        metrics = finding["metrics"]
        self.assertGreaterEqual(metrics["distinct_senders"], 20)
        self.assertGreaterEqual(metrics["pass_through_ratio"], 0.80)
        self.assertGreater(metrics["virtual_asset_out_usd"], 0)

    def test_round_value_wires_fire_on_the_trade_scenario(self):
        finding = typologies.round_value_wires("CUS-1019", 90)
        self.assertTrue(finding["triggered"])
        self.assertEqual(finding["metrics"]["wire_count"], 6)
        self.assertEqual(finding["metrics"]["distinct_amounts"], [250000.0])

    def test_rapid_in_out_fires_on_the_layering_scenario(self):
        finding = typologies.rapid_in_out("CUS-1023", 120)
        self.assertTrue(finding["triggered"])
        self.assertGreaterEqual(finding["metrics"]["matched_pairs"], 4)
        self.assertLess(finding["metrics"]["retained_pct"], 5.0)

    def test_behaviour_break_fires_for_the_vulnerable_customer(self):
        finding = typologies.behaviour_break("CUS-1044", 90)
        self.assertTrue(finding["triggered"])
        self.assertTrue(finding["metrics"]["vulnerable_customer_flag"])
        self.assertIn("GH", finding["metrics"]["new_corridors"])

    def test_every_finding_carries_a_regulatory_reference(self):
        for customer in store.customers():
            for finding in typologies.run_all(customer["customer_id"], 90):
                if finding["triggered"]:
                    self.assertTrue(
                        finding["regulatory_reference"],
                        f"{customer['customer_id']}/{finding['typology']}",
                    )
                    self.assertTrue(finding["evidence_txn_ids"] or finding["metrics"])


class Screening(unittest.TestCase):
    """Fuzzy matching has to catch variants without inventing matches."""

    def test_suffix_variant_still_matches(self):
        result = screening.screen_name("ZARIN PETROCHEMICAL FZE", "AE")
        self.assertEqual(result["verdict"], "hit")
        self.assertEqual(result["matches"][0]["matched_entry"], "ZARIN PETROCHEMICAL FZCO")

    def test_pep_beneficial_owner_matches(self):
        result = screening.screen_name("Dmitri Anatolyevich Kozlov", "KZ")
        self.assertEqual(result["verdict"], "hit")
        self.assertIn("PEP-DOMESTIC", result["matches"][0]["programs"])

    def test_unrelated_name_stays_clear(self):
        self.assertEqual(screening.screen_name("Priya Raman", "US")["verdict"], "clear")

    def test_corporate_suffixes_alone_do_not_match(self):
        # Two unrelated companies sharing only "LTD" must not collide.
        result = screening.screen_name("Northgate Systems Inc.", "US")
        self.assertEqual(result["verdict"], "clear")

    def test_adverse_media_flags_risk_tags(self):
        result = screening.search_adverse_media("Goldcoast Ventures Ltd")
        self.assertEqual(result["verdict"], "adverse_findings")
        self.assertIn("romance fraud", result["articles"][0]["risk_tags"])

    def test_neutral_coverage_is_not_adverse(self):
        result = screening.search_adverse_media("Marcus Delgado")
        self.assertEqual(result["verdict"], "neutral_coverage")


class Scorecard(unittest.TestCase):
    """Banded outcomes are pinned — a silent band change is a reporting change."""

    EXPECTED = {
        "ALT-2026-0113": ("high", "escalate_l2"),        # structuring
        "ALT-2026-0114": ("low", "close_no_sar"),        # explained home purchase
        "ALT-2026-0115": ("critical", "recommend_sar"),  # trade-based + sanctions
        "ALT-2026-0116": ("high", "escalate_l2"),        # money mule
        "ALT-2026-0117": ("critical", "recommend_sar"),  # elder exploitation
        "ALT-2026-0118": ("critical", "recommend_sar"),  # PEP layering
    }

    def test_bands_match_expected_outcomes(self):
        for alert_id, (band, disposition) in self.EXPECTED.items():
            with self.subTest(alert_id=alert_id):
                card = scoring.score_alert(alert_id)
                self.assertEqual(card["band"], band)
                self.assertEqual(card["recommended_disposition"], disposition)

    def test_the_false_positive_scores_far_below_the_true_positives(self):
        false_positive = scoring.score_alert("ALT-2026-0114")["score"]
        true_positives = [
            scoring.score_alert(a)["score"]
            for a in self.EXPECTED
            if a != "ALT-2026-0114"
        ]
        self.assertLess(false_positive, min(true_positives) - 40)

    def test_explained_activity_discounts_behavioural_typologies(self):
        card = scoring.score_alert("ALT-2026-0114")
        discounted = [f for f in card["factors"] if f.get("explained_discount_applied")]
        self.assertTrue(discounted, "home purchase should discount behavioural typologies")

    def test_scores_are_not_saturated(self):
        scores = sorted(scoring.score_alert(a)["score"] for a in self.EXPECTED)
        self.assertGreater(len(set(scores)), 4, f"scorecard lost discrimination: {scores}")

    def test_every_factor_carries_a_basis(self):
        for alert_id in self.EXPECTED:
            for factor in scoring.score_alert(alert_id)["factors"]:
                self.assertTrue(factor["basis"], f"{alert_id}/{factor['factor']}")

    def test_score_is_reproducible(self):
        first = scoring.score_alert("ALT-2026-0115")
        second = scoring.score_alert("ALT-2026-0115")
        self.assertEqual(first["score"], second["score"])
        self.assertEqual(first["factors"], second["factors"])

    def test_unknown_alert_raises(self):
        with self.assertRaises(ValueError):
            scoring.score_alert("ALT-9999-9999")


class LedgerIntegrity(unittest.TestCase):
    """The audit ledger must detect tampering, not merely store history."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._original = casefile.LEDGER
        casefile.LEDGER = Path(self._tmp.name) / "audit_ledger.jsonl"
        self._original_dir = casefile.CASEFILE_DIR

    def tearDown(self):
        casefile.LEDGER = self._original
        self._tmp.cleanup()

    def test_chain_verifies_when_untouched(self):
        for i in range(4):
            casefile.append("test_event", {"n": i})
        report = casefile.verify_ledger()
        self.assertTrue(report["verified"])
        self.assertEqual(report["entries"], 4)

    def test_altering_a_historical_entry_breaks_verification(self):
        for i in range(4):
            casefile.append("test_event", {"n": i})
        lines = casefile.LEDGER.read_text().splitlines()
        tampered = json.loads(lines[1])
        tampered["payload"]["n"] = 999
        lines[1] = json.dumps(tampered)
        casefile.LEDGER.write_text("\n".join(lines) + "\n")

        report = casefile.verify_ledger()
        self.assertFalse(report["verified"])
        self.assertEqual(report["broken_at_index"], 1)

    def test_deleting_an_entry_breaks_verification(self):
        for i in range(4):
            casefile.append("test_event", {"n": i})
        lines = casefile.LEDGER.read_text().splitlines()
        del lines[2]
        casefile.LEDGER.write_text("\n".join(lines) + "\n")
        self.assertFalse(casefile.verify_ledger()["verified"])

    def test_each_entry_chains_to_its_predecessor(self):
        casefile.append("a", {})
        casefile.append("b", {})
        entries = [json.loads(l) for l in casefile.LEDGER.read_text().splitlines()]
        self.assertEqual(entries[0]["previous_hash"], casefile.GENESIS)
        self.assertEqual(entries[1]["previous_hash"], entries[0]["entry_hash"])


@needs_client
class DispositionControls(unittest.TestCase):
    """record_disposition must refuse a case file that would not survive review."""

    def setUp(self):
        self.record = load_tool("record_disposition")
        self._tmp = tempfile.TemporaryDirectory()
        self._original_dir = casefile.CASEFILE_DIR
        self._original_ledger = casefile.LEDGER
        casefile.CASEFILE_DIR = Path(self._tmp.name)
        casefile.LEDGER = Path(self._tmp.name) / "audit_ledger.jsonl"

    def tearDown(self):
        casefile.CASEFILE_DIR = self._original_dir
        casefile.LEDGER = self._original_ledger
        self._tmp.cleanup()

    GOOD_RATIONALE = (
        "Fourteen cash deposits totalling $129,700 were made to ACC-2007-01 between "
        "14 and 29 July 2026, every one of them between $8,400 and $9,900 and none "
        "reaching the $10,000 currency transaction reporting threshold, across three "
        "branches. The customer's declared monthly turnover is $25,000. A prior "
        "STRUCT-01 alert was closed without a report in 2024. The clustering and "
        "branch spread are not consistent with ordinary convenience-store receipts."
    )

    def test_rejects_a_thin_rationale(self):
        result = self.record(
            alert_id="ALT-2026-0113",
            disposition="escalate_l2",
            rationale="Looks like structuring.",
            key_evidence_txn_ids=["TXN-000001"],
            typologies_considered=["structuring"],
        )
        self.assertTrue(result.get("rejected"))
        self.assertIn("characters", result["error"])

    def test_rejects_a_disposition_with_no_cited_evidence(self):
        result = self.record(
            alert_id="ALT-2026-0113",
            disposition="escalate_l2",
            rationale=self.GOOD_RATIONALE,
            key_evidence_txn_ids=[],
            typologies_considered=["structuring"],
        )
        self.assertTrue(result.get("rejected"))

    def test_rejects_fabricated_transaction_ids(self):
        result = self.record(
            alert_id="ALT-2026-0113",
            disposition="escalate_l2",
            rationale=self.GOOD_RATIONALE,
            key_evidence_txn_ids=["TXN-999999"],
            typologies_considered=["structuring"],
        )
        self.assertTrue(result.get("rejected"))
        self.assertIn("do not exist", result["error"])

    def test_rejects_an_unexplained_departure_from_the_scorecard(self):
        result = self.record(
            alert_id="ALT-2026-0113",
            disposition="close_no_sar",  # scorecard says escalate_l2
            rationale=self.GOOD_RATIONALE,
            key_evidence_txn_ids=self._real_txn_ids(),
            typologies_considered=["structuring"],
        )
        self.assertTrue(result.get("rejected"))
        self.assertIn("departs from the scorecard", result["error"])

    def test_accepts_an_explained_departure(self):
        result = self.record(
            alert_id="ALT-2026-0113",
            disposition="close_no_sar",
            rationale=self.GOOD_RATIONALE,
            key_evidence_txn_ids=self._real_txn_ids(),
            typologies_considered=["structuring"],
            departure_from_scorecard_reason=(
                "Documented armoured-car schedule obtained from the branch accounts "
                "for the deposit pattern in full."
            ),
        )
        self.assertTrue(result.get("recorded"))
        self.assertTrue(result["departed_from_scorecard"])

    def test_a_valid_disposition_is_recorded_and_stays_pending_review(self):
        result = self.record(
            alert_id="ALT-2026-0113",
            disposition="escalate_l2",
            rationale=self.GOOD_RATIONALE,
            key_evidence_txn_ids=self._real_txn_ids(),
            typologies_considered=["structuring", "profile_deviation"],
        )
        self.assertTrue(result["recorded"])
        self.assertEqual(result["human_review_status"], "pending")
        self.assertTrue(result["audit_entry_hash"])
        self.assertTrue(casefile.verify_ledger()["verified"])

    def test_rejects_an_invalid_disposition_value(self):
        result = self.record(
            alert_id="ALT-2026-0113",
            disposition="file_sar_immediately",
            rationale=self.GOOD_RATIONALE,
            key_evidence_txn_ids=self._real_txn_ids(),
            typologies_considered=["structuring"],
        )
        self.assertIn("Invalid disposition", result["error"])

    @staticmethod
    def _real_txn_ids() -> list[str]:
        return typologies.structuring("CUS-1007", 90)["evidence_txn_ids"][:5]


@needs_client
class SarDraftControls(unittest.TestCase):
    """submit_sar_draft must reject the deficiencies real filings fail on."""

    def setUp(self):
        self.submit = load_tool("submit_sar_draft")
        self._tmp = tempfile.TemporaryDirectory()
        self._original_dir = casefile.CASEFILE_DIR
        self._original_ledger = casefile.LEDGER
        casefile.CASEFILE_DIR = Path(self._tmp.name)
        casefile.LEDGER = Path(self._tmp.name) / "audit_ledger.jsonl"
        self.txn_ids = typologies.structuring("CUS-1007", 90)["evidence_txn_ids"]
        self.total = typologies.structuring("CUS-1007", 90)["metrics"][
            "total_below_threshold_usd"
        ]

    def tearDown(self):
        casefile.CASEFILE_DIR = self._original_dir
        casefile.LEDGER = self._original_ledger
        self._tmp.cleanup()

    NARRATIVE = (
        "This report concerns Marcus Delgado, the owner of Delgado Corner Market and "
        "a business banking customer of the institution since 17 February 2011, who "
        "between 14 July and 29 July 2026 deposited cash to business checking account "
        "ACC-2007-01 in fourteen separate transactions. Each deposit fell between "
        "$8,400 and $9,900, below the $10,000 currency transaction reporting "
        "threshold, and no single deposit during the period reached that threshold. "
        "The deposits were made across three branches, BR-014, BR-027 and BR-041. "
        "At account opening the customer declared expected monthly credits of $25,000 "
        "derived from retail convenience-store receipts. The deposits during this "
        "eighteen-day period substantially exceed that declared expectation. Following "
        "each cluster of deposits, funds were transferred to a personal savings "
        "account in four separate transfers. A prior alert on the same detection rule "
        "was closed in September 2024 without a report, on the basis that the deposit "
        "sizes were irregular and not clustered below the threshold; that "
        "characterisation does not hold for the present activity. No documentation "
        "was provided to the institution to account for the change in deposit "
        "pattern. The institution has retained the account and applied enhanced "
        "monitoring pending the outcome of this report."
    )

    def _submit(self, **overrides):
        payload = dict(
            alert_id="ALT-2026-0113",
            suspicious_activity_type="structuring",
            narrative=self.NARRATIVE,
            subjects=["Marcus Delgado"],
            activity_start_date="2026-07-14",
            activity_end_date="2026-07-29",
            total_suspicious_amount_usd=self.total,
            supporting_txn_ids=self.txn_ids,
            elements_covered=["who", "what", "when", "where", "why"],
        )
        payload.update(overrides)
        return self.submit(**payload)

    def test_a_complete_draft_is_accepted_but_never_filed(self):
        result = self._submit()
        self.assertTrue(result["accepted"], result.get("deficiencies"))
        self.assertFalse(result["filed"])
        self.assertEqual(result["status"], "pending_human_review")

    def test_rejects_a_short_narrative(self):
        result = self._submit(narrative="Customer structured cash deposits.")
        self.assertFalse(result["accepted"])

    def test_rejects_a_missing_element(self):
        result = self._submit(elements_covered=["who", "what", "when"])
        self.assertFalse(result["accepted"])
        self.assertTrue(any("where" in d for d in result["deficiencies"]))

    def test_rejects_hedging_language(self):
        result = self._submit(
            narrative=self.NARRATIVE + " The customer might be structuring deposits."
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(any("hedging" in d for d in result["deficiencies"]))

    def test_rejects_fabricated_transaction_ids(self):
        result = self._submit(supporting_txn_ids=["TXN-999999"])
        self.assertFalse(result["accepted"])

    def test_rejects_an_amount_that_does_not_reconcile(self):
        result = self._submit(total_suspicious_amount_usd=self.total * 3)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("differs from the sum" in d for d in result["deficiencies"]))

    def test_accepted_draft_is_written_to_the_ledger(self):
        self._submit()
        entries = [
            json.loads(line)
            for line in casefile.LEDGER.read_text().splitlines()
            if line.strip()
        ]
        self.assertEqual(entries[-1]["event_type"], "sar_draft_submitted_for_review")
        self.assertFalse(entries[-1]["payload"]["filed"])


@needs_client
class TippingOffControl(unittest.TestCase):
    """Customer contact must fail closed at the tool as well as at the policy."""

    def test_contact_customer_refuses(self):
        contact = load_tool("contact_customer")
        result = contact(
            customer_id="CUS-1007",
            channel="email",
            message="Please call us about recent deposits on your account.",
        )
        self.assertFalse(result["sent"])
        self.assertEqual(result["blocked_by"], "tipping_off_control")
        self.assertIn("5318(g)(2)", result["reason"])


@needs_client
class ReadableOutput(unittest.TestCase):
    """Every tool must lead with a plain-English headline.

    The transcript is the deliverable a compliance officer actually reads.
    A tool that returns only nested JSON forces the agent to paraphrase it,
    which is exactly where invented figures creep in.
    """

    READ_TOOLS = {
        "get_alert": {"alert_id": "ALT-2026-0117"},
        "list_open_alerts": {},
        "get_customer_profile": {"customer_id": "CUS-1044"},
        "get_transactions": {"customer_id": "CUS-1044", "lookback_days": 90},
        "run_typology_checks": {"customer_id": "CUS-1044", "lookback_days": 90},
        "score_alert_risk": {"alert_id": "ALT-2026-0117"},
        "screen_entity": {"name": "HELIOSPAY DIGITAL ASSETS LTD", "country": "SC"},
        "search_adverse_media": {"name": "Goldcoast Ventures Ltd"},
        "get_prior_cases": {"customer_id": "CUS-1007"},
        "verify_audit_ledger": {},
    }

    def test_every_read_tool_returns_a_summary(self):
        for name, kwargs in self.READ_TOOLS.items():
            with self.subTest(tool=name):
                result = load_tool(name)(**kwargs)
                self.assertIn("summary", result, f"{name} has no summary field")
                self.assertIsInstance(result["summary"], str)
                self.assertGreater(len(result["summary"]), 40, f"{name} summary too thin")

    def test_summaries_avoid_raw_identifiers_as_prose(self):
        # A summary is for a human. Bare snake_case tool names reading as
        # English is the smell that it was written for a parser.
        for name, kwargs in self.READ_TOOLS.items():
            with self.subTest(tool=name):
                summary = load_tool(name)(**kwargs)["summary"]
                self.assertNotIn("sys_read_inbox", summary)
                self.assertNotIn("sys_session_send", summary)

    def test_scorecard_summary_shows_the_full_working(self):
        summary = load_tool("score_alert_risk")(alert_id="ALT-2026-0117")["summary"]
        self.assertIn("RISK SCORE", summary)
        self.assertIn("recommends", summary)
        # Every contributing factor is itemised, so the total can be checked by hand.
        for factor in scoring.score_alert("ALT-2026-0117")["factors"]:
            self.assertIn(factor["factor"], summary)

    def test_typology_summary_states_what_was_ruled_out(self):
        summary = load_tool("run_typology_checks")(
            customer_id="CUS-1002", lookback_days=90
        )["summary"]
        self.assertIn("Ruled out", summary)

    def test_screening_summary_flags_the_sanctions_clock(self):
        summary = load_tool("screen_entity")(
            name="HELIOSPAY DIGITAL ASSETS LTD", country="SC"
        )["summary"]
        self.assertIn("SCREENING HIT", summary)
        self.assertIn("sanctions team", summary)

    def test_media_summary_carries_the_untrusted_warning(self):
        summary = load_tool("search_adverse_media")(name="Goldcoast Ventures Ltd")["summary"]
        self.assertIn("UNTRUSTED", summary)
        self.assertIn("never the sole basis", summary)

    def test_casefiles_are_written_outside_the_bundle(self):
        # Omnigent copies the bundle into a per-session temp directory, so a
        # ledger written relative to the package is destroyed with that copy.
        # Observed live: two completed triages produced case files under
        # /var/folders/... and a hash chain that restarted at one entry per
        # session, which proves nothing.
        from bankcore import store
        bundle = Path(__file__).resolve().parents[1]
        self.assertFalse(
            str(store.CASEFILE_DIR).startswith(str(bundle)),
            "case files must not live inside the bundle — they would be ephemeral",
        )

    def test_casefile_location_is_overridable(self):
        source = (ROOT / "bankcore" / "store.py").read_text()
        self.assertIn("ARGUS_CASEFILE_DIR", source)

    def test_agents_must_not_reference_host_style_configuration(self):
        # Stating "I'll ignore the host style preset" is itself the leak: it
        # puts the operator's tooling into a bank's case file. Observed live
        # in a QC reviewer's returned pack.
        supervisor = (ROOT / "config.yaml").read_text()
        self.assertIn("Say nothing about it", supervisor)
        for agent in ("financial_investigator", "screening_analyst", "qc_reviewer"):
            text = (ROOT / "agents" / agent / "config.yaml").read_text()
            self.assertIn("never refer to", text, agent)

    def test_supervisor_works_one_alert_per_session(self):
        # Observed live: a second alert typed into a running session made the
        # supervisor interleave two investigations, mixing two customers'
        # evidence in one context and splitting one spend budget across both —
        # the first case ran out of budget before it could record.
        supervisor = (ROOT / "config.yaml").read_text()
        self.assertIn("One alert per session", supervisor)
        self.assertIn("one alert at a time", supervisor)

    def test_agents_are_immune_to_host_style_configuration(self):
        # The claude CLI the harness drives inherits the operator's personal
        # ~/.claude plugins and hooks, which can impose a tone on a regulated
        # record. Observed live: an agent narrating about "caveman mode" in an
        # audit trail. There is no per-agent isolation knob, so the prompt
        # asserts authority over the register explicitly.
        supervisor = (ROOT / "config.yaml").read_text()
        self.assertIn("override the host environment", supervisor)
        for agent in ("financial_investigator", "screening_analyst", "qc_reviewer"):
            text = (ROOT / "agents" / agent / "config.yaml").read_text()
            self.assertIn("override the host environment", text, agent)

    def test_agents_are_instructed_to_narrate_for_a_human(self):
        supervisor = (ROOT / "config.yaml").read_text()
        self.assertIn("Narrate for the person watching", supervisor)
        for agent in ("financial_investigator", "screening_analyst", "qc_reviewer"):
            text = (ROOT / "agents" / agent / "config.yaml").read_text()
            self.assertIn("Write for a human reader", text, agent)


class BundleWiring(unittest.TestCase):
    """The Omnigent spec must load with the governance actually attached."""

    @classmethod
    def setUpClass(cls):
        try:
            from omnigent.spec import parser
        except ImportError:  # pragma: no cover - only when run outside the omnigent env
            raise unittest.SkipTest("omnigent is not importable in this interpreter")
        cls.spec = parser.parse(ROOT)

    def test_supervisor_declares_every_governance_policy(self):
        names = {p.name for p in self.spec.guardrails.policies}
        self.assertEqual(
            names,
            {
                "tipping_off_control",
                "four_eyes_on_case_record",
                "taint_untrusted_media",
                "no_case_record_after_untrusted_content",
                "taint_customer_data",
                "spawn_bounds",
                "subagent_purpose_guard",
                "cost_budget",
            },
        )

    def test_information_flow_labels_are_declared(self):
        labels = self.spec.guardrails.labels
        self.assertEqual(labels["confidentiality"].initial, "0")
        self.assertEqual(labels["integrity"].initial, "1")

    def test_all_four_sub_agents_load(self):
        self.assertEqual(
            {a.name for a in self.spec.sub_agents},
            {"financial_investigator", "screening_analyst", "narrative_writer", "qc_reviewer"},
        )

    def test_narrative_writer_has_no_data_access(self):
        writer = next(a for a in self.spec.sub_agents if a.name == "narrative_writer")
        self.assertFalse(writer.local_tools)

    def test_only_the_supervisor_can_write_to_the_record(self):
        write_tools = {"record_disposition", "submit_sar_draft"}
        self.assertTrue(write_tools <= {t.name for t in self.spec.local_tools})
        for agent in self.spec.sub_agents:
            names = {t.name for t in (agent.local_tools or [])}
            self.assertFalse(names & write_tools, f"{agent.name} can write to the record")

    def test_only_the_screening_analyst_touches_untrusted_media(self):
        holders = {
            a.name for a in self.spec.sub_agents
            if "search_adverse_media" in {t.name for t in (a.local_tools or [])}
        }
        self.assertEqual(holders, {"screening_analyst"})

    def test_untrusted_content_taints_the_reading_session(self):
        policy = next(
            p for p in self.spec.guardrails.policies if p.name == "taint_untrusted_media"
        )
        args = policy.function.arguments
        self.assertEqual(args["action"], "allow")
        self.assertEqual(args["set_labels"], {"integrity": "0"})
        self.assertEqual(args["on_tools"], ["search_adverse_media"])

    def test_a_tainted_session_cannot_write_to_the_case_record(self):
        # This is what forces media retrieval into the screening sub-agent.
        # A blanket DENY on the media tools would propagate to that
        # sub-agent and disable it — gate the WRITE on the label instead.
        policy = next(
            p for p in self.spec.guardrails.policies
            if p.name == "no_case_record_after_untrusted_content"
        )
        self.assertEqual(policy.condition, {"integrity": "0"})
        args = policy.function.arguments
        self.assertEqual(args["action"], "deny")
        self.assertEqual(
            set(args["on_tools"]), {"record_disposition", "submit_sar_draft"}
        )

    def test_sub_agents_inherit_the_supervisor_governance(self):
        # Guardrails declared on the supervisor apply to every child session,
        # so a sub-agent needs no local duplicate of them.
        analyst = next(a for a in self.spec.sub_agents if a.name == "screening_analyst")
        self.assertIsNone(analyst.guardrails)

    def test_all_three_skills_are_discovered(self):
        self.assertEqual(
            {s.name for s in self.spec.skills},
            {"alert-triage", "sar-narrative", "typology-library"},
        )

    def test_supervisor_declares_no_shell_or_filesystem_access(self):
        self.assertIsNone(self.spec.os_env)


if __name__ == "__main__":
    unittest.main(verbosity=2)
