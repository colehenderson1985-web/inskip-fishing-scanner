import { useState } from "react";
import type { Latest } from "../types";
import { fmtDate } from "../data";

const MONTHS = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];

export default function SpeciesPage({ data, locName }: { data: Latest; locName: (id: string) => string }) {
  const [open, setOpen] = useState<string | null>(data.species[0]?.id ?? null);
  return (
    <div className="wrap">
      <h2 style={{ marginTop: 10 }}>Species scanner</h2>
      <p className="small muted">Ranked by the best window in the next three days. Reports are dated and credited; a forecast never claims fish are there.</p>
      {data.species.map((s) => {
        const isOpen = open === s.id;
        return (
          <section key={s.id} className="sp">
            <header onClick={() => setOpen(isOpen ? null : s.id)} aria-expanded={isOpen}>
              <div>
                <div className="name">{s.name}</div>
                <div className="small muted">
                  <span className={`badge ${s.season === "peak" ? "green" : s.season === "shoulder" ? "amber" : ""}`}>{s.season} season</span>
                  {s.closures.some((c) => c.active) && <span className="badge red">closed season</span>}
                  {s.days_since_report == null ? "no reports in feed" : s.days_since_report === 0 ? "reported today" : `last report ${s.days_since_report} d ago`}
                  {" · "}basis: {s.basis}
                </div>
              </div>
              <div className="right"><b>{s.top_score ?? "–"}</b>{s.outlook}</div>
            </header>
            {isOpen && (
              <div style={{ marginTop: 8 }}>
                <div className="small muted" style={{ letterSpacing: ".15em", fontFamily: "var(--font-c)" }}>
                  {MONTHS.map((m, i) => <span key={i} style={{ color: s.season_months.peak.includes(i + 1) ? "var(--green)" : (s.season_months.shoulder ?? []).includes(i + 1) ? "var(--amber)" : "var(--rule)", fontWeight: 700 }}>{m}</span>)}
                  <span style={{ letterSpacing: 0, marginLeft: 8 }}>season by month</span>
                </div>
                {s.best_locations.length > 0 ? (
                  <>
                    <h3 style={{ marginTop: 10 }}>Where and when</h3>
                    <ul>{s.best_locations.map((l) => <li key={l.location}><b>{l.name}</b> {l.score}/100 — {fmtDate(l.date)} {l.window.start}–{l.window.end} <span className="muted">({l.window.label})</span></li>)}</ul>
                  </>
                ) : <p className="small muted">No scored windows in the next three days.</p>}
                {s.recent_reports.length > 0 && (
                  <>
                    <h3>Recent reports</h3>
                    <ul className="evidence">
                      {s.recent_reports.map((r, i) => (
                        <li key={i}><span className="src">{r.source}</span> · {r.date}{r.catch_date && r.catch_date !== r.date ? ` (catch ${r.catch_date})` : ""} · {r.provenance.replace("_", " ")}
                          {r.locations.length > 0 && <> · {r.locations.map(locName).join(", ")}</>}
                          {r.url && <> · <a href={r.url} target="_blank" rel="noopener">source</a></>}
                          <div className="muted">{r.excerpt}</div></li>
                      ))}
                    </ul>
                  </>
                )}
                <h3 style={{ marginTop: 10 }}>Rules</h3>
                <div className="legal">
                  <span>Min size <b>{s.legal.min_cm ?? "none"}{s.legal.min_cm ? " cm" : ""}</b></span>
                  {s.legal.max_cm && <span>Max <b>{s.legal.max_cm} cm</b></span>}
                  <span>Possession <b>{s.legal.possession}</b></span>
                  {s.closures.map((c) => <span key={c.name} style={{ color: c.active ? "var(--red)" : undefined }}>{c.name}: <b>{c.active ? "IN FORCE" : "not in force"}</b></span>)}
                  <a href={data.rules.legal_source} target="_blank" rel="noopener">Qld limits</a>
                </div>
                {(s.legal_note || s.closure_note) && <p className="small muted" style={{ marginTop: 4 }}>{s.legal_note} {s.closure_note}</p>}
                <h3 style={{ marginTop: 10 }}>Techniques</h3>
                <ul>{s.techniques.map((t, i) => <li key={i}>{t}</li>)}</ul>
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
