import type { Latest } from "../types";

export default function ReportsPage({ data, locName, spName }: { data: Latest; locName: (id: string) => string; spName: (id: string) => string }) {
  const n = data.days_since_local_report;
  return (
    <div className="wrap">
      <h2 style={{ marginTop: 10 }}>Fishing reports</h2>
      <p className="small">
        {n == null ? "No local reports in the feed yet." : n === 0 ? "A local report arrived today." : `${n} day${n === 1 ? "" : "s"} since the last report naming our waters.`}
        {" "}Public sources post weekly at best; Facebook posts from local shops arrive via the inbox.
      </p>
      {data.reports.length === 0 && <p className="empty">Nothing yet. The first refresh pulls Coastwatch and Fisho's; you can add a shop's post from Settings → Add a report.</p>}
      <ul className="rows">
        {data.reports.map((r) => (
          <li key={r.id} className="row" style={{ gridTemplateColumns: "1fr", cursor: "default" }}>
            <div className="main">
              <div className="title">
                <span className={`badge ${r.provenance === "automated" ? "teal" : r.provenance === "group_rating" ? "green" : "amber"}`}>{r.provenance === "automated" ? "automated" : r.provenance === "group_rating" ? "group" : "submitted"}</span>
                {r.credit || r.source_name}{r.section && <span className="muted"> · {r.section}</span>}
              </div>
              <div className="sub">Reported {r.report_date}{r.catch_date ? ` · fished ${r.catch_date}` : ""} <span className="muted">({r.catch_date_note})</span>{r.rating != null && <> · rated {r.rating}/5</>}</div>
              <div className="small" style={{ marginTop: 4 }}>
                {r.species.length > 0 && <>Species: {r.species.map(spName).join(", ")}. </>}
                {r.locations.length > 0 && <>Places: {r.locations.map(locName).join(", ")}.</>}
              </div>
              <p className="small" style={{ marginTop: 6 }}>{r.text}</p>
              {r.url && <a className="small" href={r.url} target="_blank" rel="noopener">Read the original</a>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
