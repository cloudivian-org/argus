"""Deterministic banking analytics behind the Argus AML triage agent.

The split is deliberate: everything that produces a *number* lives here
in plain Python, and the agents above only reason about those numbers.
That keeps figures in a regulatory filing reproducible and testable, and
it keeps the model-risk surface small enough to actually validate.
"""

from . import casefile, scoring, screening, store, typologies

__all__ = ["casefile", "scoring", "screening", "store", "typologies"]
