import type { Latest, Opportunity } from "../types";
import TideRibbon from "../components/TideRibbon";
import OppRow from "../components/OppRow";
import Freshness from "../components/Freshness";
import { fmtDate } from "../data";

export default function Home({ data, dayIndex = 0, locName, spName, onRate }:
  { data: Latest; dayIndex?: number; locName: (id: string) => string; spName: (id: string) => string; onRate: (o: Opportunity) => void }) {
  const day = data.days[dayIndex];
  const b = day.brief;
  const loc = b.best_location ? data.locations.find((l) => l.id === b.best_location!.id) : null;
  const tides = data.tides[loc?.tide_ref ?? "noosa_head"] ?? [];
  const share = async () => {
    const text = `Inskip Scanner · ${fmtDate(day.date)}\n${b.summary}\n${location.href.split("#")[0]}#/day/${day.date}`;
    try { if (navigator.share) await navigator.share({ text }); else { await navigator.clipboard.writeText(text); alert("Copied"); } } catch { /* cancelled */ }
  };
  return (
    <div className="wrap">
      <section className="brief">
        <div className="muted small">{fmtDate(day.date)} · {day.astro.moon_phase}, {Math.round(day.astro.moon_illumination * 100)}% lit</div>
        <h1 className="headline">{b.headline}</h1>
        <p className="summary">{b.summary}</p>
        <div className="meta">
          {b.best_location && <span>Best spot: <b>{b.best_location.short}</b></span>}
          {b.best_species && <span>Target: <b>{b.best_species.name}</b></span>}
          <span className={`conf ${b.confidence}`}>{b.confidence} confidence</span>
          <button className="btn secondary" style={{ padding: "2px 10px", fontSize: 14 }} onClick={share}>Share</button>
        </div>
        {b.drivers && b.drivers.length > 0 && <p className="small muted" style={{ marginTop: 8 }}>What matters today: {b.drivers.join(", ")}.</p>}
      </section>

      <TideRibbon date={day.date} tides={tides} astro={day.astro} windows={day.top} locName={locName} />
      {loc?.tide_note && <p className="small muted" style={{ marginTop: 6 }}>Tide shown for {loc.short} ({loc.tide_ref.replace("_", " ")}). {loc.tide_note}</p>}

      <h2>Best windows {dayIndex === 0 ? "today" : fmtDate(day.date)}</h2>
      {day.top.length === 0 ? <p className="empty">No scored windows. Check the data status below.</p> : (
        <ul className="rows">
          {day.top.map((o) => <OppRow key={`${o.location}-${o.species}-${o.window.start}`} o={o} locName={locName} spName={spName} onRate={onRate} />)}
        </ul>
      )}
      <p className="small muted" style={{ marginTop: 8 }}>Scores are suitability ratings from conditions, season and reports — not catch probabilities. Tap a row for the reasoning and evidence.</p>

      {data.alerts.length > 0 && (
        <>
          <h2>Access & safety</h2>
          <ul className="rows">
            {data.alerts.slice(0, 6).map((a) => (
              <li key={a.id} className="row" style={{ cursor: "default", gridTemplateColumns: "1fr" }}>
                <div className="main">
                  <div className="title"><span className={`badge ${a.severity === "closure" ? "red" : a.severity === "warning" ? "amber" : ""}`}>{a.severity}</span>{a.title}</div>
                  <div className="why" style={{ WebkitLineClamp: 3 }}>{a.summary}</div>
                  <div className="small"><a href={a.link} target="_blank" rel="noopener">{a.source}</a>{a.published && <span className="muted"> · {a.published.slice(0, 10)}</span>}</div>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}

      <h2>Data status</h2>
      <Freshness health={data.health} daysSinceReport={data.days_since_local_report} />
    </div>
  );
}
