"""Communication layer (agentic) — turns a decision into one short member notification."""
from __future__ import annotations

from datetime import datetime


def build_notification(pax_id: str, member_name: str, decision: dict, event) -> dict:
    if decision["escalated"]:
        message = (
            f"Hi {member_name}, your flight {event.flight_id} was {event.status.value}. "
            f"We found an option but it needs your OK: {decision['reasoning']} "
            f"Tap approve to confirm, or decline to handle it yourself."
        )
        action_needed = "approve_or_decline"
    else:
        message = (
            f"Hi {member_name}, your flight {event.flight_id} was {event.status.value}. "
            f"We've already rebooked you — {decision['reasoning']} "
            f"Your hotel and car have been adjusted to match. No action needed."
        )
        action_needed = "none"

    return {
        "pax_id": pax_id,
        "message": message,
        "action_needed": action_needed,
        "created_at": datetime.utcnow().isoformat(),
    }
