import { useState } from "react";
import type { Opportunity } from "../types";
import { FACTOR_LABEL, STAGE, fmtTime } from "../data";

export function ScoreChip({ score, colour, caption }: { score: number | null; colour: string; caption?: string }) {
  const cap = caption ?? (colour === "grey" ? "no data" : colour === "green" ? "good" : colour === "amber" ? "mixed" : "poor");
  return <div className={`chip ${colour}`} aria-label={`Suitability ${score ?? "unknown"}, ${cap}`}>{score ?? "–"}<small>{cap}</small></div>;
}

export default function OppRow({ o, locName, spName, showLocation = true, onRate }:
  { o: Opportunity; locName: (id: string) => string; spName: (id: string) => string; showLocation?: boolean; onRate?: (o: Opportunity) => void }) {
  const [open, setOpen] = useState(false);
  const c = o.conditions;
  return (
    <li>
      <button className={`row ${open ? "open" : ""}`} onClick={() => setOpen(!open)} aria-expanded={open}>
        <ScoreChip score={o.score} colour={o.colour} />
        <div className="main">
          <div className="head">
            <div className="title">{spName(o.species)}{showLocation && <span className="loc"> · {locName(o.location)}</span>}</div>
            <div className="when">{o.window.start}–{o.window.end}<small>{o.window.label}</small></div>
          </div>
          <div className="sub">
            <span>{c.wind_dir ?? "—"} {c.wind_kn} kn{c.wind_relation ? ` ${c.wind_relation}` : ""}</span>
            {c.seas_m != null && <span>· seas {c.seas_m} m</span>}
            {c.tide_stage && <span>· {STAGE[c.tide_stage]}</span>}
            {o.solunar?.major && <span className="tag moon">major bite</span>}
            {!o.solunar?.major && o.solunar?.minor && <span className="tag moon soft">minor bite</span>}
            <span className={`tag conf-${o.confidence}`}>{o.confidence} confidence</span>
          </div>
          <div className="why">{o.explain}</div>
        </div>
        {open && (
          <div className="detail" onClick={(e) => e.stopPropagation()}>
            <div className="kv">
              <div><b>{c.wind_dir ?? "—"} {c.wind_kn}{c.gust_kn ? `–${c.gust_kn}` : ""} kn</b><span>wind{c.effective_wind_kn != null && c.effective_wind_kn !== c.wind_kn ? ` · ${c.effective_wind_kn} kn in shelter` : ""}</span></div>
              {c.seas_m != null && <div><b>{c.seas_m} m{c.swell_period_s ? ` · ${c.swell_period_s}s` : ""}</b><span>seas · period</span></div>}
              {c.tide_next && <div><b>{c.tide_next.type === "H" ? "High" : "Low"} {fmtTime(c.tide_next.t)}</b><span>{c.tide_next.h.toFixed(1)} m{c.tide_range_m ? ` · range ${c.tide_range_m} m` : ""}</span></div>}
              {c.sst_c != null && <div><b>{c.sst_c}°C</b><span>sea surface</span></div>}
              <div><b style={{ textTransform: "capitalize" }}>{c.light}</b><span>light</span></div>
              {c.rain_24h_mm > 0 && <div><b>{c.rain_24h_mm} mm</b><span>rain last 24 h</span></div>}
            </div>
            <div className="factors" aria-label="Scoring factors">
              {Object.entries(o.factors).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
                <span key={k} className={`factor ${v >= 0.85 ? "s" : v < 0.5 ? "w" : ""}`}>{FACTOR_LABEL[k] ?? k} {Math.round(v * 100)}</span>
              ))}
            </div>
            <p className="small muted">Basis: {o.basis.join(" + ")}. A suitability rating, not a catch probability.</p>
            {o.warnings.length > 0 && <div className="note warn">{o.warnings.join(" · ")}</div>}
            {o.evidence.length > 0 && (
              <ul className="evidence">
                {o.evidence.map((e, i) => (
                  <li key={i}>
                    <span className="src">{e.credit ?? e.source}</span> · {e.date}{e.catch_date && e.catch_date !== e.date ? ` (catch ${e.catch_date})` : ""} · {e.provenance.replace("_", " ")}
                    {e.url && <> · <a href={e.url} target="_blank" rel="noopener">source</a></>}
                    <div className="muted">{e.excerpt}</div>
                  </li>
                ))}
              </ul>
            )}
            {onRate && <p style={{ marginTop: 12 }}><button className="btn secondary" onClick={() => onRate(o)}>Fished this? Rate it</button></p>}
          </div>
        )}
      </button>
    </li>
  );
}
