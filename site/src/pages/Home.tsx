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
  const best = day.top[0];
  const share = async () => {
    const text = `Inskip Scanner · ${fmtDate(day.date)}\n${b.headline}. ${b.summary}\n${location.href.split("#")[0]}#/day/${day.date}`;
    try { if (navigator.share) await navigator.share({ text }); else { await navigator.clipboard.writeText(text); alert("Copied"); } } catch { /* cancelled */ }
  };
  const closures = data.alerts.filter((a) => a.severity === "closure");
  const notices = data.alerts.filter((a) => a.severity !== "closure");
  return (
    <div>
      <section className="hero" aria-label="Daily brief">
        <div className="hero-in">
          <div className="date"><b>{fmtDate(day.date)}</b><span>{day.astro.moon_phase} · {Math.round(day.astro.moon_illumination * 100)}% lit</span></div>
          <h1>{b.headline}</h1>
          <p className="summary">{b.summary}</p>
          <div className="stats">
            <div className="stat"><span>Best spot</span><b>{b.best_location?.short ?? "—"}</b></div>
            <div className="stat"><span>Target</span><b>{b.best_species ? spName(b.best_species.id) : "—"}</b></div>
            <div className="stat wide"><span>Best window</span><b className="num">{best ? `${best.window.start}–${best.window.end}` : "—"}{best && <span style={{ display: "inline", fontSize: 12, marginLeft: 8 }}>{best.window.label}</span>}</b></div>
          </div>
          <div className="hero-actions">
            <span className={`pill conf-${b.confidence}`}>{b.confidence} confidence</span>
            {best && <span className="pill conf-none">suitability {best.score}/100</span>}
            <button className="ghost" onClick={share}>Share</button>
          </div>
        </div>
        <TideRibbon date={day.date} tides={tides} astro={day.astro} windows={day.top} locName={locName} />
      </section>
      {loc?.tide_note && <p className="notice-line">Tide shown for {loc.short} ({loc.tide_ref.replace("_", " ")}). {loc.tide_note}</p>}

      <div className="wrap">
        <div className="section"><h2>Best windows</h2><span>{dayIndex === 0 ? "today" : fmtDate(day.date)} · tap for reasoning</span></div>
        {day.top.length === 0 ? <div className="card empty">No scored windows. Check the data status below.</div> : (
          <ul className="rows">
            {day.top.map((o) => <OppRow key={`${o.location}-${o.species}-${o.window.start}`} o={o} locName={locName} spName={spName} onRate={onRate} />)}
          </ul>
        )}
        <p className="small muted" style={{ marginTop: 10 }}>Scores are suitability ratings from conditions, season and dated reports — not catch probabilities.</p>

        {(closures.length > 0 || notices.length > 0) && (
          <>
            <div className="section"><h2>Access & safety</h2><span>QPWS park alerts</span></div>
            <ul className="rows">
              {[...closures, ...notices].slice(0, 6).map((a) => (
                <li key={a.id} className="card alert">
                  <div className={`sev ${a.severity}`} />
                  <div>
                    <div className="t">{a.title}</div>
                    <div className="s">{a.summary}</div>
                    <div className="m"><a href={a.link} target="_blank" rel="noopener">{a.source}</a>{a.published && <span className="muted"> · {a.published.slice(0, 10)}</span>}</div>
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}

        <div className="section"><h2>Data status</h2><span>updates daily 04:30</span></div>
        <Freshness health={data.health} daysSinceReport={data.days_since_local_report} />
      </div>
    </div>
  );
}
