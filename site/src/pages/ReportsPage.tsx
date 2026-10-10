import { useState } from "react";
import type { Latest } from "../types";

export default function ReportsPage({ data, locName, spName }: { data: Latest; locName: (id: string) => string; spName: (id: string) => string }) {
  const n = data.days_since_local_report;
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className="wrap">
      <div className="section"><h2>Fishing reports</h2><span>{n == null ? "no local reports yet" : n === 0 ? "local report today" : `${n} d since a local report`}</span></div>
      <p className="small muted">Public sources post weekly at best. Facebook posts from local shops arrive via More → Add a report.</p>
      {data.reports.length === 0 && <div className="card empty">Nothing yet. The first refresh pulls Coastwatch and Fisho's; add a shop's post from More → Add a report.</div>}
      <ul className="rows">
        {data.reports.map((r) => (
          <li key={r.id} className={`card report ${open === r.id ? "open" : ""}`} onClick={() => setOpen(open === r.id ? null : r.id)}>
            <div className="t">
              <span className={`tag ${r.provenance === "automated" ? "teal" : r.provenance === "group_rating" ? "green" : "amber"}`}>{r.provenance === "automated" ? "automated" : r.provenance === "group_rating" ? "group" : "submitted"}</span>
              {r.kind === "guide" && <span className="tag">guide</span>}
              <span>{r.credit || r.source_name}{r.section && <span className="muted"> · {r.section}</span>}</span>
            </div>
            <div className="d">Reported {r.report_date}{r.catch_date ? ` · fished ${r.catch_date}` : ""} · {r.catch_date_note}{r.rating != null && <> · rated {r.rating}/5</>}</div>
            {(r.species.length > 0 || r.locations.length > 0) && (
              <div className="d" style={{ marginTop: 4 }}>
                {r.species.map((s) => <span key={s} className="tag" style={{ marginRight: 4 }}>{spName(s)}</span>)}
                {r.locations.map((l) => <span key={l} className="tag teal" style={{ marginRight: 4 }}>{locName(l)}</span>)}
              </div>
            )}
            <div className="x">{r.text}</div>
            {r.url && <a className="small" href={r.url} target="_blank" rel="noopener" onClick={(e) => e.stopPropagation()}>Read the original</a>}
          </li>
        ))}
      </ul>
    </div>
  );
}
