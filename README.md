# Autonomous Travel Concierge

A hackathon prototype: an agent that detects a flight disruption the moment
it happens, autonomously rebooks the flight, adjusts the hotel and rental
car, and notifies the card member — no manual action required.

Everything runs on mocked/sandboxed data. No real airline or payment
integrations.

## Architecture — three layers, kept separate on purpose

```
Ingestion (deterministic, zero LLM)
   │  POST /webhook/disruption → Pydantic validation → in-memory queue
   ▼
Decision (agentic)
   │  networkx graph of flight/hotel/car alternatives
   │  Dijkstra-style ranking (shortest_simple_paths) → top 2-3 options
   │  policy check → auto-execute OR escalate for approval
   │  ripple-effect recompute on hotel/car legs
   ▼
Communication (agentic)
   │  short natural-language notification to the member
   │  (uses a real LLM call if ANTHROPIC_API_KEY is set, else a
   │   deterministic template — the demo works with zero external deps)
```

Every autonomous decision is written to an audit trail (`/audit-log`) with:
timestamp, input event, options considered, option chosen, reasoning, and
whether it was auto-executed or escalated.

## Repo layout

```
backend/
  app/
    models.py        ingestion schemas (Pydantic)
    graph_engine.py   itinerary graph + ranked alternatives (networkx)
    policy.py         auto-execute guardrails
    agent.py          decision logic + ripple effects + justification
    communication.py  member-facing notification text
    audit.py          audit log store
    metrics.py        live pipeline metrics
    main.py           FastAPI app, in-memory event pipeline, all routes
    tests/            unit tests on the graph engine + decision logic
  fixtures/
    itineraries.json  3 seeded member itineraries (flight + hotel + car)
    inventory.json    mock Amadeus-style alternative inventory
  injector.py         standalone CLI to fire disruption events
  requirements.txt
  Dockerfile

frontend/
  src/
    App.jsx                     polling loop + layout
    api.js                      backend API client
    components/
      ItineraryBoard.jsx        boarding-pass styled itinerary cards
      LiveFeed.jsx               departure-board pipeline feed
      AuditLog.jsx               audit trail table
      StatsPanel.jsx             live metrics
      InjectorControls.jsx       fire single / storm-mode buttons
  Dockerfile

docker-compose.yml
```

## Run it — two terminals (fastest)

**Terminal 1 — backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — frontend**
```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (usually http://localhost:5173).

Optional: set `ANTHROPIC_API_KEY` in the backend's environment before
starting it to have the agent generate live LLM justifications instead of
the template fallback. Not required for the demo to work.

## Run it — Docker Compose (one command)

```bash
docker-compose up --build
```

Backend: http://localhost:8000 · Frontend: http://localhost:5173

## Running the live demo

1. Open the frontend. You'll see three seeded itineraries (Jordan Lee,
   Priya Nair, Marcus Chen).
2. Click **"Fire disruption"** — pick a member or leave it random. Watch
   the live feed step through: Detected → Decision reasoning → Ripple
   effects → Rebooked (or Pending your approval) → Notified, in a couple
   of seconds.
3. If an event escalates (no compliant option under the default policy —
   $150 max fare delta, 240 min max added delay, no cabin downgrades),
   an **Approve / Decline** control appears right on that card.
4. Click **"Storm mode (12x)"** to fire a burst of disruptions in quick
   succession and watch the pipeline keep up — this is the scalability
   demo.
5. The **stats panel** at the top shows real numbers pulled from the
   running system: detection-to-action latency, % resolved without
   escalation, and notification delivery time.
6. The **audit log** table is the full decision trail for every event.

You can also trigger events from a terminal instead of the UI:
```bash
cd backend
python injector.py single --pax-id PAX-1001
python injector.py storm --count 12
```

## Key endpoints

| Method | Path                          | Purpose                                  |
|--------|-------------------------------|-------------------------------------------|
| POST   | `/webhook/disruption`         | Ingest a flight-status event               |
| POST   | `/inject/single`               | Fire one mock disruption                   |
| POST   | `/inject/storm`                | Fire a burst of mock disruptions           |
| GET    | `/feed?since=N`                | Poll live pipeline stage events            |
| GET    | `/itineraries`                 | Seeded member itineraries                  |
| GET    | `/notifications`               | Member-facing notification log             |
| GET    | `/audit-log`                   | Full decision audit trail                  |
| GET    | `/metrics`                     | Live-measured pipeline metrics             |
| POST   | `/audit-log/{id}/approve`     | Approve an escalated rebooking             |
| POST   | `/audit-log/{id}/decline`     | Decline an escalated rebooking             |

## Tests

```bash
cd backend
pytest app/tests/ -v
```

Covers: ranking/ordering of alternatives, cabin-class preference, policy
compliance auto-execution, forced escalation under a strict policy,
ripple-effect presence, and schema rejection of a malformed disruption
status.

## Notes / what's intentionally simplified for the hackathon timeline

- State is in-memory (per the build prompt: swap for Postgres if you have
  time; Redis pub/sub only if you need true multi-process fan-out).
- The frontend polls every 1.2s rather than using SSE/WebSocket — simplest
  thing that reads as "real-time" on stage.
- The three seeded itineraries and their alternative inventory are enough
  to demo the full pipeline end-to-end; add more routes to
  `fixtures/inventory.json` if you want a richer storm-mode demo.
