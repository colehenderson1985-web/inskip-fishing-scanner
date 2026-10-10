import { useState } from "react";
import type { Latest } from "../types";
import { fmtDate } from "../data";
import { ScoreChip } from "../components/OppRow";

export default function SpeciesPage({ data, locName }: { data: Latest; locName: (id: string) => string }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className="wrap">
      <div className="section"><h2>Species scanner</h2><span>best window, next 3 days</span></div>
      <ul className="rows">
        {data.species.map((s) => {
          const isOpen = open === s.id;
          const colour = s.top_score == null ? "grey" : s.top_score >= 65 ? "green" : s.top_score >= 45 ? "amber" : "red";
          return (
            <li key={s.id} className="card sp">
              <header onClick={() => setOpen(isOpen ? null : s.id)} aria-expanded={isOpen}>
                <ScoreChip score={s.top_score} colour={colour} caption={s.top_score == null ? "not ranked" : undefined} />
                <div style={{ minWidth: 0 }}>
                  <div className="name">{s.name}</div>
                  <div className="meta">
                    <span className={`tag ${s.season === "peak" ? "green" : s.season === "shoulder" ? "amber" : ""}`}>{s.season} season</span>
                    {s.closures.some((c) => c.active) && <span className="tag red">closed season</span>}
                    <span>{s.days_since_report == null ? "no reports" : s.days_since_report === 0 ? "reported today" : `report ${s.days_since_report} d ago`}</span>
                    {s.best_locations[0] && <span>· {s.best_locations[0].name} {s.best_locations[0].window.start}</span>}
                  </div>
                </div>
              </header>
              {isOpen && (
                <div className="body">
                  <div className="small muted" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span className="months" aria-label="Season by month">{Array.from({ length: 12 }, (_, i) => <i key={i} className={s.season_months.peak.includes(i + 1) ? "p" : (s.season_months.shoulder ?? []).includes(i + 1) ? "s" : ""} />)}</span>
                    Jan → Dec · green peak, amber shoulder
                  </div>
                  {s.best_locations.length > 0 ? (
                    <>
                      <h3 style={{ marginTop: 12 }}>Where and when</h3>
                      <ul>{s.best_locations.map((l) => <li key={l.location}><b>{l.name}</b> {l.score} — {fmtDate(l.date)} {l.window.start}–{l.window.end} <span className="muted">({l.window.label})</span></li>)}</ul>
                    </>
                  ) : <p className="small muted" style={{ marginTop: 10 }}>No scored windows in the next three days.</p>}
                  {s.recent_reports.length > 0 && (
                    <>
                      <h3>Recent reports</h3>
                      <ul className="evidence" style={{ marginBottom: 10 }}>
                        {s.recent_reports.map((r, i) => (
                          <li key={i}><span className="src">{r.source}</span> · {r.date}{r.catch_date && r.catch_date !== r.date ? ` (catch ${r.catch_date})` : ""} · {r.provenance.replace("_", " ")}
                            {r.locations.length > 0 && <> · {r.locations.map(locName).join(", ")}</>}
                            {r.url && <> · <a href={r.url} target="_blank" rel="noopener">source</a></>}
                            <div className="muted">{r.excerpt}</div></li>
                        ))}
                      </ul>
                    </>
                  )}
                  <h3>Rules</h3>
                  <div className="legal">
                    <span>Min <b>{s.legal.min_cm ?? "none"}{s.legal.min_cm ? " cm" : ""}</b></span>
                    {s.legal.max_cm && <span>Max <b>{s.legal.max_cm} cm</b></span>}
                    <span>Possession <b>{s.legal.possession}</b></span>
                    {s.closures.map((c) => <span key={c.name} style={{ color: c.active ? "var(--red-ink)" : undefined }}>{c.name}: <b>{c.active ? "in force" : "not in force"}</b></span>)}
                    <a href={data.rules.legal_source} target="_blank" rel="noopener">Qld limits</a>
                  </div>
                  {(s.legal_note || s.closure_note) && <p className="small muted" style={{ marginTop: 6 }}>{s.legal_note} {s.closure_note}</p>}
                  <h3 style={{ marginTop: 12 }}>Techniques</h3>
                  <ul>{s.techniques.map((t, i) => <li key={i}>{t}</li>)}</ul>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
