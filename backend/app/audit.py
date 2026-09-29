from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any


class AuditLog:
    def __init__(self):
        self._entries: list[dict] = []

    def record(
        self,
        input_event: dict,
        options_considered: list[dict],
        option_chosen: dict | None,
        reasoning: str,
        auto_executed: bool,
        escalated: bool,
        ripple_effects: list[dict],
        timings: dict,
    ) -> dict:
        entry = {
            "audit_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "input_event": input_event,
            "options_considered": options_considered,
            "option_chosen": option_chosen,
            "reasoning": reasoning,
            "auto_executed": auto_executed,
            "escalated": escalated,
            "ripple_effects": ripple_effects,
            "timings": timings,
        }
        self._entries.append(entry)
        return entry

    def all(self) -> list[dict]:
        return list(reversed(self._entries))

    def get(self, audit_id: str) -> dict | None:
        for e in self._entries:
            if e["audit_id"] == audit_id:
                return e
        return None

    def update_status(self, audit_id: str, status: str) -> dict | None:
        e = self.get(audit_id)
        if e:
            e["approval_status"] = status
        return e


audit_log = AuditLog()
