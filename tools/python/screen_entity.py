"""Screen a name against sanctions, PEP, and internal watchlists."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omnigent_client.tools import tool  # noqa: E402

from bankcore import screening  # noqa: E402


@tool
def screen_entity(name: str, country: str | None = None) -> dict:
    """
    Screen one name against the sanctions, PEP, and internal registers.

    Matching is fuzzy on purpose — designated parties rarely appear in a
    bank's records spelled exactly as they are listed. Every candidate
    comes back with the string it matched against and a decomposed score
    so the match can be argued rather than merely asserted.

    A hit is a screening *lead*, not a conclusion. Confirming or
    discounting it is an analyst judgement that must be written down.

    :param name: Name as it appears in the bank's records.
    :param country: Optional ISO-2 country code to corroborate a match.
    :returns: Verdict (``hit``, ``possible_hit``, ``clear``) with scored
        candidate matches.
    """
    return screening.screen_name(name, country)
