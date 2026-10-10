import { useEffect, useState } from "react";
import type { Latest } from "./types";

const DATA_URL = `${import.meta.env.BASE_URL}data/latest.json`;
export const REPO = "https://github.com/colehenderson1985-web/inskip-fishing-scanner";

export function useLatest() {
  const [data, setData] = useState<Latest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(`${DATA_URL}?t=${Math.floor(Date.now() / 300000)}`, { cache: "no-cache" });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const j = (await r.json()) as Latest;
        if (cancelled) return;
        setData(j);
        try { localStorage.setItem("latest", JSON.stringify(j)); } catch { /* ignore */ }
      } catch (e: any) {
        try {
          const cached = localStorage.getItem("latest");
          if (cached && !cancelled) { setData(JSON.parse(cached)); setOffline(true); return; }
        } catch { /* ignore */ }
        if (!cancelled) setError(e?.message ?? "Failed to load");
      }
    })();
    return () => { cancelled = true; };
  }, []);
  return { data, error, offline };
}

export function hoursAgo(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  return isNaN(t) ? null : (Date.now() - t) / 3600000;
}

export function fmtAgo(iso: string | null | undefined): string {
  const h = hoursAgo(iso);
  if (h === null) return "unknown";
  if (h < 1) return `${Math.round(h * 60)} min ago`;
  if (h < 36) return `${Math.round(h)} h ago`;
  return `${Math.round(h / 24)} d ago`;
}

export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const m = iso.match(/T(\d{2}:\d{2})/);
  return m ? m[1] : iso;
}

export function fmtDate(d: string): string {
  const dt = new Date(d + "T00:00:00+10:00");
  return dt.toLocaleDateString("en-AU", { weekday: "short", day: "numeric", month: "short", timeZone: "Australia/Brisbane" });
}

export function todayISO(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: "Australia/Brisbane" });
}

export const STAGE: Record<string, string> = {
  low_turn: "bottom of tide", rising_early: "early run-in", rising_late: "last of run-in",
  high_turn: "top of tide", falling_early: "start of run-out", falling_late: "last of run-out",
};

export const FACTOR_LABEL: Record<string, string> = {
  tide: "Tide", wind: "Wind", swell: "Swell", light: "Light", season: "Season", reports: "Reports", pressure: "Pressure", rain: "Rain", lunar: "Moon",
};

export function usePrefs() {
  const [prefs, setPrefs] = useState<{ theme: "day" | "dawn"; favLocs: string[]; favSpecies: string[]; style: string; secret: string }>(() => {
    try { return { theme: "day", favLocs: [], favSpecies: [], style: "any", secret: "", ...JSON.parse(localStorage.getItem("prefs") || "{}") }; }
    catch { return { theme: "day", favLocs: [], favSpecies: [], style: "any", secret: "" }; }
  });
  useEffect(() => {
    try { localStorage.setItem("prefs", JSON.stringify(prefs)); } catch { /* ignore */ }
    document.documentElement.dataset.theme = prefs.theme;
  }, [prefs]);
  return [prefs, setPrefs] as const;
}
