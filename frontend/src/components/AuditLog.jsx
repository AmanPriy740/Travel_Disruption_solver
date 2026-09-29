import React from "react";

export default function AuditLog({ entries }) {
  return (
    <div>
      <h2 className="mono text-xs uppercase tracking-[0.2em] text-slate-400 mb-3">
        Audit Log
      </h2>
      <div className="border border-line rounded-md overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-wash mono uppercase tracking-widest text-slate-500 text-left">
              <th className="px-3 py-2 font-medium">Time</th>
              <th className="px-3 py-2 font-medium">Flight</th>
              <th className="px-3 py-2 font-medium">Decision</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Reasoning</th>
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-slate-600 mono text-xs">
                  No audited decisions yet.
                </td>
              </tr>
            )}
            {entries.map((e) => (
              <tr key={e.audit_id} className="border-t border-line/60 align-top">
                <td className="px-3 py-2 mono text-slate-500 whitespace-nowrap">
                  {new Date(e.timestamp).toLocaleTimeString()}
                </td>
                <td className="px-3 py-2 mono text-slate-200 whitespace-nowrap">
                  {e.input_event.flight_id}
                </td>
                <td className="px-3 py-2">
                  <span
                    className={`mono text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded border ${
                      e.auto_executed
                        ? "text-go border-go/40 bg-go/10"
                        : "text-signal border-signal/40 bg-signal/10"
                    }`}
                  >
                    {e.auto_executed ? "Auto-executed" : "Escalated"}
                  </span>
                </td>
                <td className="px-3 py-2 mono text-slate-400">
                  {e.approval_status || "—"}
                </td>
                <td className="px-3 py-2 text-slate-400 max-w-md">{e.reasoning}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
