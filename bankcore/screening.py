"""Name screening against the simulated sanctions / PEP / internal lists.

Real screening engines are fuzzy on purpose: sanctioned parties do not
spell their names the way your customer file does. This module models
that behaviour with a transparent, explainable score so an analyst can
see *why* a name matched rather than trusting a black box.

Scoring combines three signals:

* token overlap        — how many name words are shared
* sequence similarity  — character-level closeness (catches FZE/FZCO)
* country agreement    — same jurisdiction raises confidence

A match at or above 0.72 is reported as a hit requiring disposition;
0.60-0.72 is reported as a possible match for analyst review.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from . import store

STRONG_MATCH = 0.72
POSSIBLE_MATCH = 0.60

# Corporate suffixes carry no identifying signal — a match on "LTD"
# should never push two unrelated companies together.
_NOISE = {
    "ltd", "limited", "llc", "llp", "lp", "inc", "incorporated", "corp",
    "corporation", "co", "company", "plc", "sa", "sarl", "gmbh", "bv",
    "nv", "ag", "pte", "pty", "fze", "fzco", "fzc", "dmcc", "jsc", "ojsc",
    "the", "and", "of", "group", "holdings", "holding", "trading", "trade",
}


def _tokens(name: str) -> list[str]:
    """Normalize a name into meaningful lowercase tokens."""
    words = re.findall(r"[a-z0-9]+", name.lower())
    return [w for w in words if w not in _NOISE]


def _similarity(a: str, b: str) -> float:
    """Return an explainable 0-1 similarity between two names."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    overlap = len(set(ta) & set(tb)) / max(len(set(ta)), len(set(tb)))
    sequence = SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()
    return round(0.6 * overlap + 0.4 * sequence, 4)


def screen_name(name: str, country: str | None = None) -> dict:
    """
    Screen one name against every simulated list.

    :param name: Name as it appears in the bank's records.
    :param country: Optional ISO-2 country to corroborate a match.
    :returns: A screening result with scored candidates and a verdict.
    """
    candidates = []
    for entry in store.watchlist():
        names = [entry["entity_name"], *entry.get("aliases", [])]
        best_score = 0.0
        best_against = entry["entity_name"]
        for candidate_name in names:
            score = _similarity(name, candidate_name)
            if score > best_score:
                best_score, best_against = score, candidate_name

        country_agrees = bool(country) and country == entry.get("country")
        adjusted = min(best_score + (0.06 if country_agrees else 0.0), 1.0)
        if adjusted < POSSIBLE_MATCH:
            continue
        candidates.append(
            {
                "list_id": entry["list_id"],
                "list_name": entry["list_name"],
                "matched_entry": entry["entity_name"],
                "matched_against": best_against,
                "entity_type": entry["entity_type"],
                "country": entry.get("country"),
                "programs": entry.get("programs", []),
                "listed_date": entry.get("listed_date"),
                "remarks": entry.get("remarks"),
                "raw_score": best_score,
                "adjusted_score": round(adjusted, 4),
                "country_corroborated": country_agrees,
                "classification": "strong_match" if adjusted >= STRONG_MATCH else "possible_match",
            }
        )

    candidates.sort(key=lambda c: c["adjusted_score"], reverse=True)
    strong = [c for c in candidates if c["classification"] == "strong_match"]
    return {
        "screened_name": name,
        "screened_country": country,
        "verdict": "hit" if strong else ("possible_hit" if candidates else "clear"),
        "requires_disposition": bool(candidates),
        "match_count": len(candidates),
        "matches": candidates,
        "thresholds": {"strong_match": STRONG_MATCH, "possible_match": POSSIBLE_MATCH},
        "note": (
            "All list entries in this sandbox are fabricated records that imitate the "
            "shape of OFAC/UN/EU and PEP data. A production deployment screens against "
            "the bank's licensed list provider on the same interface."
        ),
    }


def search_adverse_media(name: str) -> dict:
    """
    Search the simulated adverse-media corpus for a subject name.

    :param name: Subject name to search for.
    :returns: Matching articles with a relevance score and risk tags.
    """
    hits = []
    for article in store.adverse_media():
        best = max(
            (_similarity(name, subject) for subject in article["subject_names"]),
            default=0.0,
        )
        if best < POSSIBLE_MATCH:
            continue
        hits.append(
            {
                "article_id": article["article_id"],
                "published": article["published"],
                "source": article["source"],
                "headline": article["headline"],
                "summary": article["summary"],
                "risk_tags": article["risk_tags"],
                "source_reliability": article["reliability"],
                "name_match_score": best,
                "matched_subject": max(
                    article["subject_names"], key=lambda s: _similarity(name, s)
                ),
            }
        )
    hits.sort(key=lambda h: (h["name_match_score"], h["published"]), reverse=True)
    adverse = [h for h in hits if h["risk_tags"]]
    return {
        "searched_name": name,
        "verdict": "adverse_findings" if adverse else ("neutral_coverage" if hits else "no_coverage"),
        "article_count": len(hits),
        "adverse_article_count": len(adverse),
        "articles": hits,
        "note": (
            "Simulated corpus. Treat media as UNVERIFIED third-party content: it may "
            "support an escalation but must never be the sole basis for one, and it "
            "must not be quoted verbatim into a regulatory filing."
        ),
    }
