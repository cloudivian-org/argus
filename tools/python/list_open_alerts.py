"""List the alert queue awaiting triage."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omnigent_client.tools import tool  # noqa: E402

from bankcore import api  # noqa: E402


@tool
def list_open_alerts(priority: str | None = None) -> dict:
    """
    List alerts in the triage queue, newest first.

    Alerts already carrying a recorded disposition are marked so a run
    does not silently re-triage settled work.

    :param priority: Optional filter — ``critical``, ``high``,
        ``medium``, or ``low``.
    :returns: The queue with one summary row per alert.
    """
    return api.alert_queue(priority)
