"""Tamper-evident case file and audit ledger.

Regulators do not ask whether the model was clever. They ask who decided
what, on what evidence, when, and whether the record can be shown to be
unaltered. This module is the answer to that question.

Every write appends one entry to ``casefiles/audit_ledger.jsonl``. Each
entry carries the SHA-256 of the previous entry, so the ledger is a hash
chain: altering or deleting any historical entry breaks verification for
every entry after it. ``verify_ledger()`` re-walks the chain.

Nothing here can file a SAR. The agent can only produce a draft in
``pending_human_review``; moving it to filed is a human act performed in
the bank's own reporting system.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .store import CASEFILE_DIR

LEDGER = CASEFILE_DIR / "audit_ledger.jsonl"
GENESIS = "0" * 64

VALID_DISPOSITIONS = {
    "close_no_sar",
    "close_with_edd",
    "escalate_l2",
    "recommend_sar",
}


def _now() -> str:
    """Return an RFC 3339 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _digest(payload: dict) -> str:
    """Return the SHA-256 of a canonical JSON encoding of ``payload``."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _tail_hash() -> str:
    """Return the hash of the last ledger entry, or the genesis value."""
    if not LEDGER.exists():
        return GENESIS
    last = None
    for line in LEDGER.read_text().splitlines():
        if line.strip():
            last = line
    if last is None:
        return GENESIS
    return json.loads(last)["entry_hash"]


def append(event_type: str, payload: dict[str, Any]) -> dict:
    """
    Append one entry to the tamper-evident audit ledger.

    :param event_type: What happened, e.g. ``disposition_recorded``.
    :param payload: The event body.
    :returns: The stored ledger entry, including its chain hashes.
    """
    CASEFILE_DIR.mkdir(parents=True, exist_ok=True)
    prev = _tail_hash()
    body = {
        "timestamp": _now(),
        "event_type": event_type,
        "actor": os.environ.get("OMNIGENT_ACTOR", "argus-aml-agent"),
        "actor_type": "ai_agent",
        "previous_hash": prev,
        "payload": payload,
    }
    entry = {**body, "entry_hash": _digest(body)}
    with LEDGER.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


def verify_ledger() -> dict:
    """
    Re-walk the hash chain and report whether the ledger is intact.

    :returns: A verification report with the entry count and, on
        failure, the index of the first broken link.
    """
    if not LEDGER.exists():
        return {"verified": True, "entries": 0, "note": "No audit entries yet."}
    prev = GENESIS
    entries = 0
    for index, line in enumerate(LEDGER.read_text().splitlines()):
        if not line.strip():
            continue
        entry = json.loads(line)
        body = {k: v for k, v in entry.items() if k != "entry_hash"}
        if entry["previous_hash"] != prev or _digest(body) != entry["entry_hash"]:
            return {
                "verified": False,
                "entries": entries,
                "broken_at_index": index,
                "note": "Ledger integrity check FAILED — an entry was altered or removed.",
            }
        prev = entry["entry_hash"]
        entries += 1
    return {
        "verified": True,
        "entries": entries,
        "head_hash": prev,
        "note": "Hash chain intact; no entry has been altered or removed.",
    }


def case_path(alert_id: str) -> Path:
    """Return the case-file path for one alert."""
    return CASEFILE_DIR / f"{alert_id}.json"


def write_case(alert_id: str, document: dict) -> Path:
    """
    Write or replace the structured case file for an alert.

    The case file is the working document; the ledger is the immutable
    record of how it got that way.

    :param alert_id: Alert the case belongs to.
    :param document: The full case document.
    :returns: The path written.
    """
    CASEFILE_DIR.mkdir(parents=True, exist_ok=True)
    path = case_path(alert_id)
    path.write_text(json.dumps(document, indent=2) + "\n")
    return path


def read_case(alert_id: str) -> dict | None:
    """Return the stored case file for an alert, if one exists."""
    path = case_path(alert_id)
    return json.loads(path.read_text()) if path.exists() else None
