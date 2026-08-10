"""Outbound customer contact — present so the tipping-off control has something to stop.

Disclosing that a suspicious activity report exists, or is being
considered, is a criminal offence in most AML regimes (in the US, 31 USC
5318(g)(2)). An agent that can reach a customer during an investigation
is a tipping-off incident waiting to happen.

Rather than omit the capability and prove nothing, the bundle registers
it and then blocks it at the guardrail layer, so the control is
demonstrable rather than merely asserted. This tool refuses on its own
as well: the deny is the boundary, and a boundary you cannot see fail is
one you cannot trust.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omnigent_client.tools import tool  # noqa: E402


@tool
def contact_customer(customer_id: str, channel: str, message: str) -> dict:
    """
    Send an outbound message to a customer. Blocked during investigations.

    Do not call this tool while an alert is under investigation. Contact
    with a subject during a suspicious-activity review risks disclosing
    the existence of the review, which is a criminal offence, and it can
    destroy the evidentiary value of the case.

    Where genuine customer contact is warranted — a scam intervention for
    a vulnerable customer, for example — it is initiated by the branch or
    the fraud team under a separate procedure that keeps the SAR
    invisible. Recommend that pathway in your report instead of using
    this tool.

    :param customer_id: Customer to contact.
    :param channel: Contact channel.
    :param message: Message body.
    :returns: A refusal explaining the control that applies.
    """
    return {
        "sent": False,
        "blocked_by": "tipping_off_control",
        "customer_id": customer_id,
        "channel": channel,
        "reason": (
            "Outbound customer contact is prohibited for an agent operating on an "
            "open suspicious-activity investigation. Disclosing the existence of a "
            "report or an investigation to its subject is an offence under 31 USC "
            "5318(g)(2) and equivalent regimes."
        ),
        "correct_pathway": (
            "Record the recommendation in the case file. Branch or fraud-team "
            "intervention, where warranted, is initiated by a human under a "
            "procedure designed not to disclose the report."
        ),
    }
