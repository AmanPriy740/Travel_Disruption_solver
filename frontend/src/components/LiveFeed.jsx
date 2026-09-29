import React, { useState } from "react";

const STEPS = ["Detected", "Decision reasoning", "Ripple effects", "Resolved", "Notified"];

function stepIndex(stage) {
  if (stage === "Rebooked" || stage === "Pending your approval") return 3;
  return STEPS.indexOf(stage);
}

function statusColor(caseItem) {
  if (caseItem.escalated) return "text-signal border-signal/40";
  if (caseItem.stage === "Notified") return "text-go border-go/40";
  return "text-slate-300 border-line";
}

function Stepper({ caseItem }) {
  const idx = Math.max(0, stepIndex(caseItem.stage));
  return (
    <div className="flex items-center gap-1.5 mt-2">
      {STEPS.map((s, i) => (
        <React.Fragment key={s}>
          <div
            className={`w-2 h-2 rounded-full ${
              i < idx
                ? "bg-go"
                : i === idx
                ? caseItem.escalated && i === 3
                  ? "bg-signal pulse-dot"
                  : "bg-signal pulse-dot"
                : "bg-line"
            }`}
          />
          {i < STEPS.length - 1 && <div className="w-4 h-px bg-line" />}
        </React.Fragment>
      ))}
    </div>
  );
}

function CaseRow({ caseItem, onApprove, onDecline }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      className={`board-row rounded-md border bg-panel px-4 py-3 ${statusColor(caseItem)}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="mono text-sm font-semibold text-slate-100">
              {caseItem.flight_id}
            </span>
            <span className="mono text-[10px] uppercase tracking-widest text-slate-500">
              {caseItem.pax_id}
            </span>
            <span className="mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded bg-wash border border-line text-slate-400">
              {caseItem.status}
            </span>
          </div>
          <div className="mono text-xs uppercase tracking-widest mt-1">
            {caseItem.stage}
            {caseItem.approvalStatus && (
              <span className="ml-2 text-slate-400 normal-case">
                · {caseItem.approvalStatus}
              </span>
            )}
          </div>
          <Stepper caseItem={caseItem} />
        </div>
        <button
          onClick={() => setOpen((o) => !o)}
          className="mono text-[10px] uppercase tracking-widest text-slate-500 hover:text-slate-200 shrink-0"
        >
          {open ? "hide" : "details"}
        </button>
      </div>

      {open && (
        <div className="mt-3 pt-3 border-t border-line/60 space-y-2 text-sm">
          {caseItem.reasoning && (
            <p className="text-slate-300">{caseItem.reasoning}</p>
          )}
          {caseItem.rippleEffects?.length > 0 && (
            <div>
              <div className="mono text-[10px] uppercase tracking-widest text-slate-500 mb-1">
                Ripple effects
              </div>
              <ul className="space-y-1">
                {caseItem.rippleEffects.map((r, i) => (
                  <li key={i} className="text-xs text-slate-400">
                    <span className="text-slate-200 mono">{r.leg}.{r.field}</span>{" "}
                    {r.from} → {r.to}
                    <span className="text-slate-600"> — {r.reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {caseItem.message && (
            <div className="text-xs text-slate-400 bg-wash rounded p-2 border border-line">
              {caseItem.message}
            </div>
          )}
          {caseItem.stage === "Pending your approval" &&
            caseItem.approvalStatus === "pending" && (
              <div className="flex gap-2 pt-1">
                <button
                  onClick={() => onApprove(caseItem.auditId)}
                  className="mono text-xs uppercase tracking-widest px-3 py-1.5 rounded bg-go/20 text-go border border-go/40 hover:bg-go/30"
                >
                  Approve
                </button>
                <button
                  onClick={() => onDecline(caseItem.auditId)}
                  className="mono text-xs uppercase tracking-widest px-3 py-1.5 rounded bg-alert/20 text-alert border border-alert/40 hover:bg-alert/30"
                >
                  Decline
                </button>
              </div>
            )}
        </div>
      )}
    </div>
  );
}

export default function LiveFeed({ cases, onApprove, onDecline }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="mono text-xs uppercase tracking-[0.2em] text-slate-400">
          Live Disruption Feed
        </h2>
        <span className="mono text-[10px] text-slate-600">
          Detected → Decision → Ripple → Rebooked/Pending → Notified
        </span>
      </div>
      <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
        {cases.length === 0 && (
          <div className="mono text-xs text-slate-600 border border-dashed border-line rounded-md p-6 text-center">
            No disruptions yet — fire the injector to see the pipeline run.
          </div>
        )}
        {cases.map((c) => (
          <CaseRow
            key={c.eventId}
            caseItem={c}
            onApprove={onApprove}
            onDecline={onDecline}
          />
        ))}
      </div>
    </div>
  );
}
