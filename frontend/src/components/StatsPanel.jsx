import React from "react";

function Stat({ label, value, accent }) {
  return (
    <div className="rounded-md border border-line bg-panel px-4 py-3">
      <div className="mono text-[10px] uppercase tracking-widest text-slate-500">{label}</div>
      <div className={`mono text-2xl font-semibold mt-1 ${accent || "text-slate-100"}`}>
        {value}
      </div>
    </div>
  );
}

export default function StatsPanel({ metrics }) {
  if (!metrics) return null;
  return (
    <div>
      <h2 className="mono text-xs uppercase tracking-[0.2em] text-slate-400 mb-3">
        Live Metrics
      </h2>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Stat label="Disruptions handled" value={metrics.disruptions_received} />
        <Stat
          label="Resolved w/o escalation"
          value={`${metrics.resolved_without_escalation_pct}%`}
          accent="text-go"
        />
        <Stat label="Escalated" value={metrics.escalated_count} accent="text-signal" />
        <Stat
          label="Avg detect→action"
          value={`${metrics.avg_detection_to_action_ms}ms`}
        />
        <Stat
          label="Avg notify latency"
          value={`${metrics.avg_notification_delivery_ms}ms`}
        />
      </div>
    </div>
  );
}
