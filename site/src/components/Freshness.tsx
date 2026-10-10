import type { Health } from "../types";
import { fmtAgo, hoursAgo } from "../data";

const CATS: Record<string, string> = { weather: "Wind & weather", marine: "Swell & SST", bom: "BOM forecast", tides: "Tides", alerts: "Park alerts", reports: "Fishing reports" };

export default function Freshness({ health, daysSinceReport }: { health: Health; daysSinceReport: number | null }) {
  const byCat: Record<string, { ok: boolean; last: string | null; err: string | null }> = {};
  for (const [, s] of Object.entries(health.sources)) {
    const c = byCat[s.category] ?? { ok: true, last: null, err: null };
    c.ok = c.ok && s.ok;
    if (!s.ok && s.error) c.err = s.error;
    if (s.last_success && (!c.last || s.last_success > c.last)) c.last = s.last_success;
    byCat[s.category] = c;
  }
  const genH = hoursAgo(health.generated_at);
  return (
    <div>
      <p className="small">
        Last update <b>{fmtAgo(health.generated_at)}</b>{genH != null && genH > 30 && <span className="badge amber" style={{ marginLeft: 6 }}>stale</span>}
        {" · "}next scheduled {fmtAgo(health.next_scheduled).replace("ago", "").trim() ? new Date(health.next_scheduled).toLocaleString("en-AU", { weekday: "short", hour: "2-digit", minute: "2-digit", timeZone: "Australia/Brisbane" }) : "—"}
        {" · "}pipeline <b>{health.overall}</b>
      </p>
      <div className="fresh">
        {Object.entries(CATS).map(([k, label]) => {
          const c = byCat[k];
          const cls = !c ? "" : c.ok ? "ok" : c.last ? "stale" : "bad";
          return (
            <div key={k} className={cls} title={c?.err ?? ""}>
              <b>{label}</b>
              {!c ? "not run" : c.ok ? `ok · ${fmtAgo(c.last)}` : c.last ? `stale · last ${fmtAgo(c.last)}` : "unavailable"}
              {k === "reports" && daysSinceReport != null && <div>{daysSinceReport === 0 ? "local report today" : `${daysSinceReport} d since local report`}</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
