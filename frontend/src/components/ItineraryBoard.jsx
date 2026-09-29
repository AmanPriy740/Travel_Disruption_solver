import React from "react";

function fmtTime(iso) {
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function Stub({ label, value, wide }) {
  return (
    <div className={wide ? "col-span-2" : ""}>
      <div className="mono text-[10px] uppercase tracking-widest text-slate-500">{label}</div>
      <div className="mono text-sm text-slate-100 truncate">{value}</div>
    </div>
  );
}

export default function ItineraryBoard({ itineraries }) {
  return (
    <div>
      <h2 className="mono text-xs uppercase tracking-[0.2em] text-slate-400 mb-3">
        Member Itineraries
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {itineraries.map((it) => (
          <div
            key={it.pax_id}
            className="relative rounded-md border border-line bg-panel overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 py-2 border-b border-dashed border-line bg-wash">
              <span className="mono text-sm font-semibold text-signal">
                {it.flight.carrier.toUpperCase()} {it.flight.flight_number}
              </span>
              <span className="mono text-[10px] text-slate-500">{it.pax_id}</span>
            </div>
            <div className="px-4 py-3 grid grid-cols-2 gap-3">
              <Stub label="Member" value={it.member_name} wide />
              <Stub label="Route" value={`${it.flight.origin} → ${it.flight.destination}`} />
              <Stub label="Cabin" value={it.flight.cabin_class} />
              <Stub label="Departs" value={fmtTime(it.flight.departure)} wide />
              <Stub label="Hotel" value={it.hotel.name} wide />
              <Stub label="Car" value={`${it.car.vendor} · ${it.car.class}`} wide />
            </div>
            {/* perforation notch, boarding-pass style */}
            <div className="absolute -left-2 top-[38px] w-4 h-4 rounded-full bg-ink border border-line" />
            <div className="absolute -right-2 top-[38px] w-4 h-4 rounded-full bg-ink border border-line" />
          </div>
        ))}
      </div>
    </div>
  );
}
