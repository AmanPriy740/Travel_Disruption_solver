from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Metrics:
    disruptions_received: int = 0
    resolved_without_escalation: int = 0
    escalated: int = 0
    detection_to_action_ms: list[float] = field(default_factory=list)
    notification_delivery_ms: list[float] = field(default_factory=list)

    def record_pipeline_run(
        self,
        auto_executed: bool,
        detection_to_action_ms: float,
        notification_delivery_ms: float,
    ):
        self.disruptions_received += 1
        if auto_executed:
            self.resolved_without_escalation += 1
        else:
            self.escalated += 1
        self.detection_to_action_ms.append(detection_to_action_ms)
        self.notification_delivery_ms.append(notification_delivery_ms)

    def snapshot(self) -> dict:
        n = self.disruptions_received
        avg = lambda xs: round(sum(xs) / len(xs), 1) if xs else 0.0
        return {
            "disruptions_received": n,
            "resolved_without_escalation_pct": (
                round(100 * self.resolved_without_escalation / n, 1) if n else 0.0
            ),
            "escalated_count": self.escalated,
            "avg_detection_to_action_ms": avg(self.detection_to_action_ms),
            "avg_notification_delivery_ms": avg(self.notification_delivery_ms),
            "p95_detection_to_action_ms": _p95(self.detection_to_action_ms),
        }


def _p95(xs: list[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    idx = max(0, int(len(s) * 0.95) - 1)
    return round(s[idx], 1)


metrics = Metrics()
