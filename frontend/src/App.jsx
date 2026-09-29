import React, { useEffect, useRef, useState } from "react";
import { api } from "./api";
import ItineraryBoard from "./components/ItineraryBoard.jsx";
import LiveFeed from "./components/LiveFeed.jsx";
import AuditLog from "./components/AuditLog.jsx";
import StatsPanel from "./components/StatsPanel.jsx";
import InjectorControls from "./components/InjectorControls.jsx";

const POLL_MS = 1200;

function reduceFeedToCases(feedEvents) {
  const byId = new Map();
  for (const ev of feedEvents) {
    if (!ev.event_id) continue; // e.g. "Approved by member" global events handled separately
    const existing = byId.get(ev.event_id) || {
      eventId: ev.event_id,
      flight_id: ev.flight_id,
      pax_id: ev.pax_id,
      status: ev.status,
      stage: ev.stage,
      escalated: false,
      approvalStatus: null,
      rippleEffects: [],
      reasoning: null,
      message: null,
      auditId: null,
    };
    existing.stage = ev.stage;
    if (ev.flight_id) existing.flight_id = ev.flight_id;
    if (ev.pax_id) existing.pax_id = ev.pax_id;
    if (ev.status) existing.status = ev.status;
    if (ev.ripple_effects) existing.rippleEffects = ev.ripple_effects;
    if (ev.reasoning) existing.reasoning = ev.reasoning;
    if (ev.escalated !== undefined) existing.escalated = ev.escalated;
    if (ev.message) existing.message = ev.message;
    if (ev.audit_id) existing.auditId = ev.audit_id;
    if (ev.stage === "Pending your approval" && !existing.approvalStatus) {
      existing.approvalStatus = "pending";
    }
    byId.set(ev.event_id, existing);
  }
  return Array.from(byId.values()).reverse();
}

export default function App() {
  const [itineraries, setItineraries] = useState([]);
  const [feedEvents, setFeedEvents] = useState([]);
  const [auditEntries, setAuditEntries] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const sinceRef = useRef(0);

  useEffect(() => {
    api.itineraries().then(setItineraries).catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const [feedRes, audit, m] = await Promise.all([
          api.feed(sinceRef.current),
          api.auditLog(),
          api.metrics(),
        ]);
        if (cancelled) return;
        if (feedRes.events.length) {
          setFeedEvents((prev) => [...prev, ...feedRes.events]);
        }
        sinceRef.current = feedRes.next_since;
        setAuditEntries(audit);
        setMetrics(m);
      } catch (e) {
        // backend not reachable yet — keep polling silently
      }
    }
    poll();
    const id = setInterval(poll, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const cases = reduceFeedToCases(feedEvents);

  const handleApprove = async (auditId) => {
    await api.approve(auditId);
  };
  const handleDecline = async (auditId) => {
    await api.decline(auditId);
  };

  return (
    <div className="min-h-screen">
      <header className="border-b border-line px-6 py-5 flex items-center justify-between">
        <div>
          <div className="mono text-[10px] uppercase tracking-[0.3em] text-signal">
            Concierge Ops
          </div>
          <h1 className="text-xl font-semibold text-slate-100 mt-0.5">
            Autonomous Travel Concierge
          </h1>
        </div>
        <div className="mono text-[10px] uppercase tracking-widest text-slate-500 text-right">
          <div>Ingestion · Decision · Communication</div>
          <div className="text-slate-600">no manual action required</div>
        </div>
      </header>

      <main className="px-6 py-6 max-w-7xl mx-auto space-y-8">
        <InjectorControls
          itineraries={itineraries}
          onInjectSingle={(paxId) => api.injectSingle(paxId)}
          onInjectStorm={(count) => api.injectStorm(count)}
        />

        <StatsPanel metrics={metrics} />

        <ItineraryBoard itineraries={itineraries} />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <LiveFeed cases={cases} onApprove={handleApprove} onDecline={handleDecline} />
          <AuditLog entries={auditEntries} />
        </div>
      </main>
    </div>
  );
}
