from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .agent import decide
from .audit import audit_log
from .communication import build_notification
from .graph_engine import ItineraryGraph
from .metrics import metrics
from .models import DisruptionEvent, IngestResult

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

app = FastAPI(title="Autonomous Travel Concierge")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory state (demo-scale; swap for Postgres/Redis for anything real)
# ---------------------------------------------------------------------------
ITINERARIES: dict = json.loads((FIXTURES_DIR / "itineraries.json").read_text())
INVENTORY: dict = json.loads((FIXTURES_DIR / "inventory.json").read_text())

event_queue: "asyncio.Queue[dict]" = asyncio.Queue()
feed: list[dict] = []          # visible pipeline stages, newest last
notifications: list[dict] = []
rejected_events: list[dict] = []

MAX_FEED = 500


def _push_feed(item: dict):
    feed.append(item)
    if len(feed) > MAX_FEED:
        del feed[0 : len(feed) - MAX_FEED]


# ---------------------------------------------------------------------------
# Layer 1: Ingestion (deterministic, zero LLM calls)
# ---------------------------------------------------------------------------
@app.post("/webhook/disruption", response_model=IngestResult)
async def webhook_disruption(payload: dict):
    try:
        event = DisruptionEvent(**payload)
    except ValidationError as e:
        rejected_events.append({"payload": payload, "errors": e.errors()})
        return IngestResult(accepted=False, reason=str(e.errors()))

    event_id = str(uuid.uuid4())
    received_at = time.monotonic()
    _push_feed(
        {
            "event_id": event_id,
            "stage": "Detected",
            "flight_id": event.flight_id,
            "pax_id": event.pax_id,
            "status": event.status.value,
            "timestamp": time.time(),
        }
    )
    await event_queue.put({"event_id": event_id, "event": event, "received_at": received_at})
    return IngestResult(accepted=True, event_id=event_id)


# ---------------------------------------------------------------------------
# Layer 2 + 3 consumer: Decision (agentic) -> Communication (agentic)
# ---------------------------------------------------------------------------
async def process_events():
    while True:
        job = await event_queue.get()
        try:
            await _process_one(job)
        except Exception as exc:  # keep the pipeline alive even if one event misbehaves
            _push_feed(
                {
                    "event_id": job["event_id"],
                    "stage": "Error",
                    "error": str(exc),
                    "timestamp": time.time(),
                }
            )
        finally:
            event_queue.task_done()


async def _process_one(job: dict):
    event_id = job["event_id"]
    event = job["event"]
    received_at = job["received_at"]

    itinerary = ITINERARIES.get(event.pax_id)
    if not itinerary:
        _push_feed(
            {
                "event_id": event_id,
                "stage": "Error",
                "error": f"Unknown pax_id {event.pax_id}",
                "timestamp": time.time(),
            }
        )
        return

    action_start = time.monotonic()
    detection_to_action_ms = (action_start - received_at) * 1000

    graph = ItineraryGraph(itinerary, INVENTORY)
    ranked = graph.rank_options(top_k=3)

    _push_feed(
        {
            "event_id": event_id,
            "stage": "Decision reasoning",
            "options_considered": [o.to_dict() for o in ranked],
            "timestamp": time.time(),
        }
    )
    await asyncio.sleep(0.15)  # small pacing delay so the demo feed is legible on stage

    decision = decide(itinerary, ranked)

    _push_feed(
        {
            "event_id": event_id,
            "stage": "Ripple effects",
            "ripple_effects": decision["ripple_effects"],
            "timestamp": time.time(),
        }
    )
    await asyncio.sleep(0.1)

    stage_label = "Rebooked" if decision["auto_executed"] else "Pending your approval"
    _push_feed(
        {
            "event_id": event_id,
            "stage": stage_label,
            "chosen": decision["chosen"],
            "reasoning": decision["reasoning"],
            "auto_executed": decision["auto_executed"],
            "escalated": decision["escalated"],
            "timestamp": time.time(),
        }
    )

    decision_finalized_at = time.monotonic()
    notification = build_notification(
        event.pax_id, itinerary["member_name"], decision, event
    )
    notification["event_id"] = event_id
    notification["audit_id"] = None  # filled in below
    notification_delivery_ms = (time.monotonic() - decision_finalized_at) * 1000

    audit_entry = audit_log.record(
        input_event=event.model_dump(mode="json"),
        options_considered=[o.to_dict() for o in ranked],
        option_chosen=decision["chosen"],
        reasoning=decision["reasoning"],
        auto_executed=decision["auto_executed"],
        escalated=decision["escalated"],
        ripple_effects=decision["ripple_effects"],
        timings={
            "detection_to_action_ms": round(detection_to_action_ms, 1),
            "notification_delivery_ms": round(notification_delivery_ms, 1),
        },
    )
    if decision["escalated"]:
        audit_entry["approval_status"] = "pending"
    notification["audit_id"] = audit_entry["audit_id"]
    notifications.append(notification)

    _push_feed(
        {
            "event_id": event_id,
            "stage": "Notified",
            "message": notification["message"],
            "action_needed": notification["action_needed"],
            "audit_id": audit_entry["audit_id"],
            "timestamp": time.time(),
        }
    )

    metrics.record_pipeline_run(
        auto_executed=decision["auto_executed"],
        detection_to_action_ms=detection_to_action_ms,
        notification_delivery_ms=notification_delivery_ms,
    )


@app.on_event("startup")
async def _start_worker():
    asyncio.create_task(process_events())


# ---------------------------------------------------------------------------
# Read endpoints for the frontend (polling)
# ---------------------------------------------------------------------------
@app.get("/itineraries")
async def get_itineraries():
    return list(ITINERARIES.values())


@app.get("/feed")
async def get_feed(since: int = 0):
    return {"events": feed[since:], "next_since": len(feed)}


@app.get("/notifications")
async def get_notifications():
    return list(reversed(notifications))


@app.get("/audit-log")
async def get_audit_log():
    return audit_log.all()


@app.get("/metrics")
async def get_metrics():
    return metrics.snapshot()


@app.get("/rejected-events")
async def get_rejected_events():
    return rejected_events


# ---------------------------------------------------------------------------
# Escalation approve/decline
# ---------------------------------------------------------------------------
@app.post("/audit-log/{audit_id}/approve")
async def approve(audit_id: str):
    entry = audit_log.update_status(audit_id, "approved")
    if not entry:
        raise HTTPException(404, "audit entry not found")
    _push_feed(
        {
            "stage": "Approved by member",
            "audit_id": audit_id,
            "timestamp": time.time(),
        }
    )
    return entry


@app.post("/audit-log/{audit_id}/decline")
async def decline(audit_id: str):
    entry = audit_log.update_status(audit_id, "declined")
    if not entry:
        raise HTTPException(404, "audit entry not found")
    _push_feed(
        {
            "stage": "Declined by member",
            "audit_id": audit_id,
            "timestamp": time.time(),
        }
    )
    return entry


# ---------------------------------------------------------------------------
# Demo mechanics: disruption injector
# ---------------------------------------------------------------------------
import random

SAMPLE_STATUSES = ["cancelled", "delayed", "missed_connection"]


def _random_event_for(pax_id: str) -> dict:
    itinerary = ITINERARIES[pax_id]
    status = random.choice(SAMPLE_STATUSES)
    payload = {
        "flight_id": itinerary["flight"]["flight_id"],
        "status": status,
        "pax_id": pax_id,
        "original_itinerary": f"ITIN-{pax_id}",
    }
    if status == "delayed":
        payload["delay_minutes"] = random.choice([45, 90, 150, 300])
    return payload


@app.post("/inject/single")
async def inject_single(pax_id: str | None = None):
    pax_id = pax_id or random.choice(list(ITINERARIES.keys()))
    payload = _random_event_for(pax_id)
    return await webhook_disruption(payload)


@app.post("/inject/storm")
async def inject_storm(count: int = 12):
    results = []
    pax_ids = list(ITINERARIES.keys())
    for i in range(count):
        pax_id = pax_ids[i % len(pax_ids)]
        payload = _random_event_for(pax_id)
        results.append(await webhook_disruption(payload))
        await asyncio.sleep(0.05)
    return {"fired": len(results), "results": results}


@app.get("/")
async def root():
    return {
        "service": "autonomous-travel-concierge",
        "docs": "/docs",
        "endpoints": [
            "POST /webhook/disruption",
            "GET /feed?since=0",
            "GET /itineraries",
            "GET /notifications",
            "GET /audit-log",
            "GET /metrics",
            "POST /inject/single",
            "POST /inject/storm",
            "POST /audit-log/{id}/approve",
            "POST /audit-log/{id}/decline",
        ],
    }
