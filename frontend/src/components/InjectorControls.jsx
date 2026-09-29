import React, { useState } from "react";

export default function InjectorControls({ itineraries, onInjectSingle, onInjectStorm }) {
  const [paxId, setPaxId] = useState("");
  const [busy, setBusy] = useState(false);

  const run = async (fn) => {
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-md border border-line bg-panel px-4 py-3 flex flex-wrap items-center gap-3">
      <span className="mono text-[10px] uppercase tracking-widest text-slate-500">
        Disruption Injector
      </span>
      <select
        value={paxId}
        onChange={(e) => setPaxId(e.target.value)}
        className="mono text-xs bg-wash border border-line rounded px-2 py-1.5 text-slate-200"
      >
        <option value="">Random member</option>
        {itineraries.map((it) => (
          <option key={it.pax_id} value={it.pax_id}>
            {it.pax_id} — {it.member_name}
          </option>
        ))}
      </select>
      <button
        disabled={busy}
        onClick={() => run(() => onInjectSingle(paxId || undefined))}
        className="mono text-xs uppercase tracking-widest px-3 py-1.5 rounded bg-signal/20 text-signal border border-signal/40 hover:bg-signal/30 disabled:opacity-40"
      >
        Fire disruption
      </button>
      <button
        disabled={busy}
        onClick={() => run(() => onInjectStorm(12))}
        className="mono text-xs uppercase tracking-widest px-3 py-1.5 rounded bg-alert/20 text-alert border border-alert/40 hover:bg-alert/30 disabled:opacity-40"
      >
        Storm mode (12x)
      </button>
      {busy && <span className="mono text-[10px] text-slate-500">running…</span>}
    </div>
  );
}
