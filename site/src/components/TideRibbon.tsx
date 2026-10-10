import type { Astro, Opportunity, Tide } from "../types";

/** Today's tide curve with recommended windows and daylight drawn on it. */
export default function TideRibbon({ date, tides, astro, windows, locName }:
  { date: string; tides: Tide[]; astro: Astro; windows: Opportunity[]; locName: (id: string) => string }) {
  const W = 720, H = 150, padL = 8, padR = 8, top = 26, bottom = 118;
  const d0 = Date.parse(date + "T00:00:00+10:00");
  const d1 = d0 + 86400000;
  const x = (t: number) => padL + ((t - d0) / 86400000) * (W - padL - padR);
  const pts = tides
    .map((r) => ({ t: Date.parse(r.t.length === 16 ? r.t + ":00+10:00" : r.t), h: r.h, type: r.type, mod: r.modelled }))
    .filter((p) => !isNaN(p.t) && p.t >= d0 - 8 * 3600000 && p.t <= d1 + 8 * 3600000)
    .sort((a, b) => a.t - b.t);
  if (pts.length < 2) return <div className="ribbon"><p className="muted small" style={{ padding: 12 }}>Tide data unavailable for this day.</p></div>;
  const hs = pts.map((p) => p.h);
  const hmin = Math.min(...hs) - 0.1, hmax = Math.max(...hs) + 0.1;
  const y = (h: number) => bottom - ((h - hmin) / (hmax - hmin)) * (bottom - top);
  // cosine interpolation between turns
  const path: string[] = [];
  const area: string[] = [];
  const step = 10 * 60000;
  let first = true;
  for (let t = Math.max(d0, pts[0].t); t <= Math.min(d1, pts[pts.length - 1].t); t += step) {
    let i = 0;
    while (i < pts.length - 2 && pts[i + 1].t < t) i++;
    const a = pts[i], b = pts[i + 1];
    const f = (t - a.t) / (b.t - a.t);
    const h = a.h + (b.h - a.h) * (1 - Math.cos(Math.PI * f)) / 2;
    const cmd = `${first ? "M" : "L"}${x(t).toFixed(1)},${y(h).toFixed(1)}`;
    path.push(cmd); area.push(cmd); first = false;
  }
  const lastX = path.length ? path[path.length - 1].slice(1).split(",")[0] : x(d1);
  const firstX = path.length ? path[0].slice(1).split(",")[0] : x(d0);
  const areaPath = `${area.join(" ")} L${lastX},${bottom} L${firstX},${bottom} Z`;
  const sr = Date.parse(astro.sunrise), ss = Date.parse(astro.sunset);
  const now = Date.now();
  const colour: Record<string, string> = { green: "var(--green)", amber: "var(--amber)", red: "var(--red)", grey: "var(--grey)" };
  const wins = windows.slice(0, 5).map((w) => ({
    s: Date.parse(w.window.start_iso + ":00+10:00"), e: Date.parse(w.window.end_iso + ":00+10:00"), c: w.colour, lab: locName(w.location), score: w.score,
  }));
  return (
    <div className="ribbon" aria-label="Tide curve for the day with recommended windows">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img">
        <rect className="night" x={x(d0)} y={top - 6} width={Math.max(0, x(sr) - x(d0))} height={bottom - top + 6} />
        <rect className="night" x={x(ss)} y={top - 6} width={Math.max(0, x(d1) - x(ss))} height={bottom - top + 6} />
        <path className="fill" d={areaPath} />
        <path className="curve" d={path.join(" ")} vectorEffect="non-scaling-stroke" />
        {wins.map((w, i) => (
          <g key={i} className="win">
            <rect x={x(w.s)} y={bottom + 4} width={Math.max(4, x(w.e) - x(w.s))} height={7} rx={2} fill={colour[w.c]} />
            <text className="lab" x={x(w.s) + 2} y={bottom + 24} fill={colour[w.c]}>{w.lab} {w.score}</text>
          </g>
        ))}
        {pts.filter((p) => p.t >= d0 && p.t < d1).map((p, i) => (
          <g key={i}>
            <circle cx={x(p.t)} cy={y(p.h)} r={3.5} fill="var(--teal)" />
            <text className="lab strong" x={x(p.t)} y={p.type === "H" ? y(p.h) - 9 : y(p.h) + 17} textAnchor="middle">
              {new Date(p.t).toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Australia/Brisbane" })} {p.h.toFixed(1)}m{p.mod ? "*" : ""}
            </text>
          </g>
        ))}
        {[0, 6, 12, 18].map((h) => (
          <g key={h}>
            <line className="axis" x1={x(d0 + h * 3600000)} x2={x(d0 + h * 3600000)} y1={top - 6} y2={bottom} />
            <text className="lab" x={x(d0 + h * 3600000) + 3} y={14}>{String(h).padStart(2, "0")}:00</text>
          </g>
        ))}
        <text className="lab" x={x(sr) + 3} y={14} fill="var(--amber)">☀ {new Date(sr).toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Australia/Brisbane" })}</text>
        <text className="lab" x={x(ss) - 54} y={14} fill="var(--amber)">☾ {new Date(ss).toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Australia/Brisbane" })}</text>
        {now >= d0 && now < d1 && <line className="now" x1={x(now)} x2={x(now)} y1={top - 6} y2={bottom + 12} />}
      </svg>
      <div className="ribbon-key">
        <span><i style={{ background: "var(--teal)" }} />tide height</span>
        <span><i style={{ background: "var(--green)" }} />recommended window (score)</span>
        <span><i style={{ background: "var(--ink)", opacity: .15 }} />dark</span>
        {pts.some((p) => p.mod) && <span>* modelled tide, lower confidence</span>}
      </div>
    </div>
  );
}
