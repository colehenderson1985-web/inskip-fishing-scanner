import type { Astro, Opportunity, Tide } from "../types";

/** Parse "YYYY-MM-DDTHH:MM", "…:SS", with or without a "+10:00" offset, as AEST. */
export function parseAEST(iso: string): number {
  let s = iso;
  const m = s.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})(:\d{2})?(.*)$/);
  if (m) s = m[1] + (m[2] ?? ":00") + (m[3] || "+10:00");
  return Date.parse(s);
}

/** Today's tide curve with recommended windows and daylight drawn on it. */
export default function TideRibbon({ date, tides, astro, windows, locName }:
  { date: string; tides: Tide[]; astro: Astro; windows: Opportunity[]; locName: (id: string) => string }) {
  const W = 720, H = 190, padL = 8, padR = 8, top = 26, bottom = 112;
  const d0 = Date.parse(date + "T00:00:00+10:00");
  const d1 = d0 + 86400000;
  const x = (t: number) => padL + ((t - d0) / 86400000) * (W - padL - padR);
  const pts = tides
    .map((r) => ({ t: parseAEST(r.t), h: r.h, type: r.type, mod: r.modelled }))
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
    s: parseAEST(w.window.start_iso), e: parseAEST(w.window.end_iso), c: w.colour, lab: locName(w.location), score: w.score,
  }));
  return (
    <div className="ribbon" aria-label="Tide curve for the day with recommended windows">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img">
        <rect className="night" x={x(d0)} y={top - 6} width={Math.max(0, x(sr) - x(d0))} height={bottom - top + 6} />
        <rect className="night" x={x(ss)} y={top - 6} width={Math.max(0, x(d1) - x(ss))} height={bottom - top + 6} />
        <path className="fill" d={areaPath} />
        <path className="curve" d={path.join(" ")} vectorEffect="non-scaling-stroke" />
        {wins.map((w, i) => {
          const y0 = bottom + 26 + i * 13;
          const x0 = x(w.s), x1 = Math.max(x0 + 4, x(w.e));
          const labelRight = x1 + 4 + (w.lab.length + 3) * 6.5 < W - padR;
          return (
            <g key={i} className="win">
              <rect x={x0} y={y0} width={x1 - x0} height={8} rx={2} fill={colour[w.c]} />
              <text className="lab" x={labelRight ? x1 + 4 : x0 - 4} y={y0 + 8} textAnchor={labelRight ? "start" : "end"} fill={colour[w.c]}>{w.lab} {w.score}</text>
            </g>
          );
        })}
        {pts.filter((p) => p.t >= d0 && p.t < d1).map((p, i) => (
          <g key={i}>
            <circle cx={x(p.t)} cy={y(p.h)} r={3.5} fill="var(--teal)" />
            <text className="lab strong" x={x(p.t)} y={p.type === "H" ? y(p.h) - 9 : y(p.h) + 17} textAnchor="middle">
              {new Date(p.t).toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Australia/Brisbane" })} {p.h.toFixed(1)}m{p.mod ? "*" : ""}
            </text>
          </g>
        ))}
        {[0, 6, 12, 18].map((h) => {
          const hx = x(d0 + h * 3600000);
          const clash = Math.abs(hx - x(sr)) < 70 || Math.abs(hx - x(ss)) < 70;
          return (
            <g key={h}>
              <line className="axis" x1={hx} x2={hx} y1={top - 6} y2={bottom} />
              {!clash && <text className="lab" x={hx + 3} y={14}>{String(h).padStart(2, "0")}:00</text>}
            </g>
          );
        })}
        <text className="lab" x={x(sr) + 3} y={14} fill="var(--amber)">☀ {new Date(sr).toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Australia/Brisbane" })}</text>
        <text className="lab" x={x(ss) + 3} y={14} fill="var(--amber)">☾ {new Date(ss).toLocaleTimeString("en-AU", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Australia/Brisbane" })}</text>
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
