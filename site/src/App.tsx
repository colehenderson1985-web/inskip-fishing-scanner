import { Suspense, lazy, useEffect, useMemo, useState } from "react";
import { fmtAgo, hoursAgo, useLatest, usePrefs } from "./data";
import type { Opportunity } from "./types";
import Home from "./pages/Home";
const MapPage = lazy(() => import("./pages/MapPage"));
import SpeciesPage from "./pages/SpeciesPage";
import WindowsPage from "./pages/WindowsPage";
import ReportsPage from "./pages/ReportsPage";
import ForecastPage from "./pages/ForecastPage";
import SettingsPage from "./pages/SettingsPage";

type Route = { page: string; arg?: string };

function parseHash(): Route {
  const h = location.hash.replace(/^#\/?/, "");
  const [page, arg] = h.split("/");
  return { page: page || "home", arg };
}

const TABS: [string, string, string][] = [
  ["home", "Home", "M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"],
  ["map", "Map", "M9 3l6 2 6-2v16l-6 2-6-2-6 2V5zM9 3v16M15 5v16"],
  ["species", "Species", "M2 12s4-6 10-6 10 6 10 6-4 6-10 6S2 12 2 12zm10-2a2 2 0 1 0 0 4 2 2 0 0 0 0-4z"],
  ["windows", "Windows", "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 5v5l3 3"],
  ["reports", "Reports", "M5 3h10l4 4v14H5zM15 3v4h4M8 12h8M8 16h8"],
  ["forecast", "Forecast", "M4 18h16M4 14c3-4 6-4 9 0s6 4 7 0M4 10c3-4 6-4 9 0s6 4 7 0"],
  ["settings", "More", "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zm8 4a8 8 0 0 1-.1 1.3l2 1.6-2 3.4-2.4-1a8 8 0 0 1-2.2 1.3L15 21H9l-.3-2.4a8 8 0 0 1-2.2-1.3l-2.4 1-2-3.4 2-1.6A8 8 0 0 1 4 12a8 8 0 0 1 .1-1.3l-2-1.6 2-3.4 2.4 1a8 8 0 0 1 2.2-1.3L9 3h6l.3 2.4a8 8 0 0 1 2.2 1.3l2.4-1 2 3.4-2 1.6c.1.4.1.9.1 1.3z"],
];

export default function App() {
  const { data, error, offline } = useLatest();
  const [prefs] = usePrefs();
  const [route, setRoute] = useState<Route>(parseHash());
  const [dayIndex, setDayIndex] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [prefill, setPrefill] = useState<Opportunity | null>(null);
  useEffect(() => {
    const f = () => setRoute(parseHash());
    addEventListener("hashchange", f); return () => removeEventListener("hashchange", f);
  }, []);
  useEffect(() => {
    if (!data) return;
    if (route.page === "location" && route.arg) { setSelected(route.arg); location.hash = "#/map"; }
    if (route.page === "day" && route.arg) { const i = data.days.findIndex((d) => d.date === route.arg); if (i >= 0) setDayIndex(i); location.hash = "#/forecast"; }
  }, [route, data]);
  useEffect(() => { document.documentElement.dataset.theme = prefs.theme; }, [prefs.theme]);

  const locName = useMemo(() => { const m = new Map(data?.locations.map((l) => [l.id, l.short])); return (id: string) => m.get(id) ?? id; }, [data]);
  const spName = useMemo(() => { const m = new Map(data?.species.map((s) => [s.id, s.short ?? s.name])); return (id: string) => m.get(id) ?? id; }, [data]);
  const onRate = (o: Opportunity) => { setPrefill(o); location.hash = "#/settings"; setTimeout(() => document.getElementById("rate")?.scrollIntoView({ behavior: "smooth" }), 50); };

  if (error) return <div className="wrap"><h1 style={{ marginTop: 40 }}>Can't load the scanner</h1><p>{error}. If this is a fresh deployment, the first daily refresh hasn't run yet — it runs at 04:30 AEST, or can be started from GitHub Actions.</p></div>;
  if (!data) return <div className="wrap"><p className="muted" style={{ marginTop: 40 }}>Loading…</p></div>;

  const genH = hoursAgo(data.generated_at);
  const stale = genH != null && genH > 30;
  const closures = data.alerts.filter((a) => a.severity === "closure");
  const bigWarn = data.bom.marine_warning || closures.length > 0;
  const notices = data.alerts.filter((a) => a.severity !== "closure").length;
  const page = route.page;
  return (
    <>
      {page !== "map" && (
        <header className="topbar">
          <div className="brand">Inskip Scanner<small>Rainbow Beach to Tin Can Bay</small></div>
          <div className={`updated ${stale ? "stale" : ""}`}>{offline ? "offline copy · " : ""}{stale ? "stale · " : ""}{fmtAgo(data.generated_at)}</div>
        </header>
      )}
      {page === "home" && bigWarn && (
        <div className={`warnbar ${data.bom.marine_warning ? "" : "amber"}`}>
          {data.bom.marine_warning ? "BOM marine warning current for this coast — check the coastal waters forecast." : "Access closures in force."}
          {closures.length > 0 && <ul>{closures.slice(0, 3).map((a) => <li key={a.id}>{a.title}</li>)}</ul>}
        </div>
      )}
      {page === "home" && !bigWarn && notices > 0 && (
        <div className="wrap"><p className="small muted" style={{ margin: "6px 0 0" }}>{notices} park notice{notices > 1 ? "s" : ""} for the area — see Access & safety below.</p></div>
      )}
      {page === "home" && <Home data={data} dayIndex={0} locName={locName} spName={spName} onRate={onRate} />}
      {page === "map" && <Suspense fallback={<div className="wrap"><p className="muted" style={{ marginTop: 40 }}>Loading map…</p></div>}><MapPage data={data} dayIndex={dayIndex} locName={locName} spName={spName} selected={selected} setSelected={setSelected} onRate={onRate} /></Suspense>}
      {page === "species" && <SpeciesPage data={data} locName={locName} />}
      {page === "windows" && <WindowsPage data={data} locName={locName} spName={spName} onRate={onRate} />}
      {page === "reports" && <ReportsPage data={data} locName={locName} spName={spName} />}
      {page === "forecast" && <ForecastPage data={data} dayIndex={dayIndex} setDayIndex={setDayIndex} locName={locName} spName={spName} onRate={onRate} />}
      {page === "settings" && <SettingsPage data={data} prefill={prefill} />}
      <nav className="tabs" aria-label="Sections">
        {TABS.map(([id, label, d]) => (
          <a key={id} href={`#/${id}`} className={page === id ? "active" : ""} aria-current={page === id ? "page" : undefined}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d={d} /></svg>
            {label}
          </a>
        ))}
      </nav>
    </>
  );
}
