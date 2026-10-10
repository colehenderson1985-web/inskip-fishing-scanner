import type { Astro, Opportunity, Tide } from "../types";

/** Parse "YYYY-MM-DDTHH:MM", "…:SS", with or without a "+10:00" offset, as AEST. */
export function parseAEST(iso: string): number {
  let s = iso;
  const m = s.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})(:\d{2})?(.*)$/);
  if (m) s = m[1] + (m[2] ?? ":00") + (m[3] || "+10:00");
  return Date.parse(s);
}

const hhmm = (t: number) => new Date(t).toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Australia/Brisbane" });

/** Today's tide curve with recommended windows and daylight drawn on it. Lives inside the hero. */
export default function TideRibbon({ date, tides, astro, windows, locName }:
  { date: string; tides: Tide[]; astro: Astro; windows: Opportunity[]; locName: (id: string) => string }) {
  const W = 720, H = 196, padL = 10, padR = 10, top = 30, bottom = 118;
  const d0 = Date.parse(date + "T00:00:00+10:00");
  const d1 = d0 + 86400000;
  const x = (t: number) => padL + ((t - d0) / 86400000) * (W - padL - padR);
  const pts = tides
    .map((r) => ({ t: parseAEST(r.t), h: r.h, type: r.type, mod: r.modelled }))
    .filter((p) => !isNaN(p.t) && p.t >= d0 - 8 * 3600000 && p.t <= d1 + 8 * 3600000)
    .sort((a, b) => a.t - b.t);
  if (pts.length < 2) return <div className="ribbon"><p className="small" style={{ padding: 14, color: "#9fb3bc" }}>Tide data unavailable for this day.</p></div>;
  const hs = pts.map((p) => p.h);
  const hmin = Math.min(...hs) - 0.15, hmax = Math.max(...hs) + 0.15;
  const y = (h: number) => bottom - ((h - hmin) / (hmax - hmin)) * (bottom - top);
  const path: string[] = [];
  const step = 10 * 60000;
  for (let t = Math.max(d0, pts[0].t); t <= Math.min(d1, pts[pts.length - 1].t); t += step) {
    let i = 0;
    while (i < pts.length - 2 && pts[i + 1].t < t) i++;
    const a = pts[i], b = pts[i + 1];
    const f = (t - a.t) / (b.t - a.t);
    const h = a.h + (b.h - a.h) * (1 - Math.cos(Math.PI * f)) / 2;
    path.push(`${path.length ? "L" : "M"}${x(t).toFixed(1)},${y(h).toFixed(1)}`);
  }
  const lastX = path.length ? path[path.length - 1].slice(1).split(",")[0] : x(d1);
  const firstX = path.length ? path[0].slice(1).split(",")[0] : x(d0);
  const areaPath = `${path.join(" ")} L${lastX},${bottom} L${firstX},${bottom} Z`;
  const sr = Date.parse(astro.sunrise), ss = Date.parse(astro.sunset);
  const now = Date.now();
  const colour: Record<string, string> = { green: "#3fc477", amber: "#f0a73a", red: "#ef6b57", grey: "#8d959c" };
  // one bar per location (its best window), max 4, ordered by start time
  const seen = new Set<string>();
  const wins = windows.filter((w) => { if (seen.has(w.location)) return false; seen.add(w.location); return true; }).slice(0, 4)
    .map((w) => ({ s: parseAEST(w.window.start_iso), e: parseAEST(w.window.end_iso), c: w.colour, lab: locName(w.location), score: w.score }))
    .sort((a, b) => a.s - b.s);
  return (
    <div className="ribbon" aria-label="Tide curve for the day with recommended windows">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img">
        <defs>
          <linearGradient id="tideFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#4fd1c7" stopOpacity=".35" /><stop offset="1" stopColor="#4fd1c7" stopOpacity=".02" />
          </linearGradient>
        </defs>
        <rect className="night" x={x(d0)} y={top - 10} width={Math.max(0, x(sr) - x(d0))} height={bottom - top + 10} />
        <rect className="night" x={x(ss)} y={top - 10} width={Math.max(0, x(d1) - x(ss))} height={bottom - top + 10} />
        <path className="fill" d={areaPath} />
        <path className="curve" d={path.join(" ")} vectorEffect="non-scaling-stroke" />
        {[0, 6, 12, 18].map((h) => {
          const hx = x(d0 + h * 3600000);
          const clash = Math.abs(hx - x(sr)) < 64 || Math.abs(hx - x(ss)) < 64;
          return (
            <g key={h}>
              <line className="axis" x1={hx} x2={hx} y1={top - 10} y2={bottom} />
              {!clash && <text className="lab" x={hx + 4} y={16}>{String(h).padStart(2, "0")}:00</text>}
            </g>
          );
        })}
        <g className="sun"><circle cx={x(sr)} cy={11} r={3.5} /><text className="lab sun" x={x(sr) + 7} y={15}>{hhmm(sr)}</text></g>
        <g className="sun"><circle cx={x(ss)} cy={11} r={3.5} /><text className="lab sun" x={x(ss) + 7} y={15}>{hhmm(ss)}</text></g>
        {pts.filter((p) => p.t >= d0 && p.t < d1).map((p, i) => (
          <g key={i}>
            <circle cx={x(p.t)} cy={y(p.h)} r={4} fill="#0e1a21" stroke="#4fd1c7" strokeWidth={2.5} />
            <text className="lab strong" x={x(p.t)} y={p.type === "H" ? y(p.h) - 10 : y(p.h) + 18} textAnchor="middle">
              {hhmm(p.t)} · {p.h.toFixed(1)} m{p.mod ? "*" : ""}
            </text>
          </g>
        ))}
        {wins.map((w, i) => {
          const y0 = bottom + 20 + i * 14;
          const x0 = x(w.s), x1 = Math.max(x0 + 6, x(w.e));
          const labelRight = x1 + 6 + (w.lab.length + 3) * 6.6 < W - padR;
          return (
            <g key={i}>
              <rect x={x0} y={y0} width={x1 - x0} height={8} rx={4} fill={colour[w.c]} />
              <text className="lab" x={labelRight ? x1 + 6 : x0 - 6} y={y0 + 8} textAnchor={labelRight ? "start" : "end"} fill="#cfdbe0">{w.lab} <tspan fill={colour[w.c]} fontWeight={700}>{w.score}</tspan></text>
            </g>
          );
        })}
        {now >= d0 && now < d1 && <line className="now" x1={x(now)} x2={x(now)} y1={top - 10} y2={bottom + 12} />}
      </svg>
      <div className="ribbon-key">
        <span><i style={{ background: "#4fd1c7" }} />tide</span>
        <span><i style={{ background: "#3fc477" }} />best windows by location</span>
        <span><i style={{ background: "#ff8a6b" }} />now</span>
        {pts.some((p) => p.mod) && <span>* modelled tide</span>}
      </div>
    </div>
  );
}
