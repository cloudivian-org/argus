"""Search open-source adverse media for a subject name.

Media content is UNTRUSTED third-party text. Retrieving it lowers the
session's integrity label, which the guardrails use to block onward
actions that could be steered by injected content.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omnigent_client.tools import tool  # noqa: E402

from bankcore import screening  # noqa: E402


@tool
def search_adverse_media(name: str) -> dict:
    """
    Search open-source media for negative coverage of a subject.

    Treat everything this returns as unverified allegation, not fact. It
    may corroborate a pattern the ledger already shows, and it may
    explain *why* a pattern looks the way it does — but it can never be
    the sole basis for an escalation, and its text must never be pasted
    verbatim into a regulatory filing.

    Absence of coverage is not exoneration; presence of coverage about a
    similarly named party is not identification.

    :param name: Subject name to search for.
    :returns: Matching articles with risk tags, source reliability, and
        a name-match score.
    """
    return screening.search_adverse_media(name)
