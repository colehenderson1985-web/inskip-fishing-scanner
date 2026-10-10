import { useState } from "react";
import type { Latest, Opportunity } from "../types";
import Home from "./Home";
import { fmtDate } from "../data";
import { ScoreChip } from "../components/OppRow";

export default function ForecastPage({ data, dayIndex, setDayIndex, locName, spName, onRate }:
  { data: Latest; dayIndex: number; setDayIndex: (i: number) => void; locName: (id: string) => string; spName: (id: string) => string; onRate: (o: Opportunity) => void }) {
  const [cmpA, setCmpA] = useState(data.locations[0]?.id ?? "");
  const [cmpB, setCmpB] = useState(data.locations[3]?.id ?? "");
  const day = data.days[dayIndex];
  const wxA = data.weather[cmpA]; const wxB = data.weather[cmpB];
  return (
    <div>
      <div className="wrap">
        <div className="section"><h2>Plan ahead</h2><span>7-day outlook</span></div>
        <div className="daypick" role="tablist">
          {data.days.map((d, i) => (
            <button key={d.date} className={i === dayIndex ? "on" : ""} onClick={() => setDayIndex(i)} role="tab" aria-selected={i === dayIndex}>
              {i === 0 ? "Today" : i === 1 ? "Tomorrow" : fmtDate(d.date).split(" ")[0]}
              <small>{d.brief.best_location ? `${d.brief.best_location.short} ${d.brief.best_location.score}` : "—"}</small>
            </button>
          ))}
        </div>
        <p className="small muted">Confidence drops with distance: days 1–2 use fresh forecasts, days 5–7 are indicative only.</p>
      </div>
      <Home data={data} dayIndex={dayIndex} locName={locName} spName={spName} onRate={onRate} />
      <div className="wrap">
        <div className="section"><h2>Compare two locations</h2><span>{fmtDate(day.date)}</span></div>
        <div className="filters">
          <select value={cmpA} onChange={(e) => setCmpA(e.target.value)} aria-label="First location">{data.locations.map((l) => <option key={l.id} value={l.id}>{l.short}</option>)}</select>
          <select value={cmpB} onChange={(e) => setCmpB(e.target.value)} aria-label="Second location">{data.locations.map((l) => <option key={l.id} value={l.id}>{l.short}</option>)}</select>
        </div>
        <div className="cmp">
          {[cmpA, cmpB].map((id) => {
            const ld = day.locations[id]; const loc = data.locations.find((l) => l.id === id)!;
            if (!ld || !loc) return <div key={id} />;
            return (
              <div key={id} className="card col">
                <ScoreChip score={ld.score} colour={ld.colour} />
                <div className="v" style={{ fontSize: 17 }}>{loc.short}</div>
                {ld.conditions && <><div className="k">Wind</div><div className="v">{ld.conditions.wind_dir} {ld.conditions.wind_kn} kn · {ld.conditions.wind_relation}</div></>}
                {ld.conditions?.seas_m != null && <><div className="k">Seas</div><div className="v">{ld.conditions.seas_m} m</div></>}
                {ld.best_window && <><div className="k">Best window</div><div className="v">{ld.best_window.start}–{ld.best_window.end}</div></>}
                <div className="k">Target</div><div className="v">{ld.best_species.slice(0, 2).map((s) => spName(s.species)).join(", ") || "—"}</div>
                <div className="k">Access</div><div className="v">{loc.access.vehicle === "4wd" ? "4WD" : loc.access.vehicle === "walk" ? "Walk-in" : "2WD"}{loc.access.permit !== "none" ? " · permit" : ""} · {loc.line_limit.lines} lines</div>
                {ld.warnings.length > 0 && <div className="note warn small" style={{ marginTop: 6 }}>{ld.warnings[0]}</div>}
              </div>
            );
          })}
        </div>
        <div className="section"><h2>Wind & seas</h2><span>next 7 days</span></div>
        <Spark series={wxA} v="wind_speed_10m" label={`${locName(cmpA)} wind (kn)`} colour="var(--teal)" />
        <Spark series={wxB} v="wind_speed_10m" label={`${locName(cmpB)} wind (kn)`} colour="var(--amber)" />
        {Object.entries(data.marine).map(([k, m]) => <Spark key={k} series={m} v="wave_height" label={`${m.name ?? k} seas (m)`} colour="var(--ink-2)" />)}
      </div>
    </div>
  );
}

function Spark({ series, v, label, colour }: { series: any; v: string; label: string; colour: string }) {
  if (!series?.time?.length || !series[v]) return null;
  const vals: (number | null)[] = series[v];
  const n = vals.length; const W = 720, H = 70;
  const max = Math.max(...vals.filter((x): x is number => x != null), 1);
  const pts = vals.map((x, i) => x == null ? null : `${(i / (n - 1)) * W},${H - 8 - (x / max) * (H - 20)}`).filter(Boolean).join(" ");
  const days = series.time.map((t: string, i: number) => ({ t, i })).filter(({ t }: { t: string }) => t.endsWith("T00:00"));
  return (
    <div className="card" style={{ marginBottom: 10, padding: "10px 12px 6px" }}>
      <div className="small" style={{ display: "flex", justifyContent: "space-between" }}><b>{label}</b> <span className="muted">max {max.toFixed(1)}</span></div>
      <svg className="spark" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        {days.map(({ t, i }: { t: string; i: number }) => <g key={t}><line x1={(i / (n - 1)) * W} x2={(i / (n - 1)) * W} y1={0} y2={H} stroke="var(--rule)" /><text x={(i / (n - 1)) * W + 4} y={13} fontSize={13} fontWeight={600} fill="var(--ink-3)">{t.slice(8, 10)}/{t.slice(5, 7)}</text></g>)}
        <polyline points={pts} fill="none" stroke={colour} strokeWidth={2} vectorEffect="non-scaling-stroke" />
      </svg>
    </div>
  );
}
