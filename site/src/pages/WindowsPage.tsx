import { useMemo, useState } from "react";
import type { Latest, Opportunity } from "../types";
import OppRow from "../components/OppRow";
import { fmtDate } from "../data";

export default function WindowsPage({ data, locName, spName, onRate }: { data: Latest; locName: (id: string) => string; spName: (id: string) => string; onRate: (o: Opportunity) => void }) {
  const [loc, setLoc] = useState("all");
  const [sp, setSp] = useState("all");
  const [style, setStyle] = useState("any");
  const rows = useMemo(() => {
    const out: { date: string; o: Opportunity }[] = [];
    for (const d of data.days.slice(0, 3)) for (const o of d.top) out.push({ date: d.date, o });
    return out.filter(({ o }) => {
      if (loc !== "all" && o.location !== loc) return false;
      if (sp !== "all" && o.species !== sp) return false;
      if (style !== "any") {
        const t = data.locations.find((l) => l.id === o.location)?.type;
        if (style === "surf" && !(t === "surf_beach" || t === "headland")) return false;
        if (style === "estuary" && !(t === "estuary" || t === "sheltered_strait")) return false;
      }
      return true;
    }).sort((a, b) => (a.o.window.start_iso < b.o.window.start_iso ? -1 : 1));
  }, [data, loc, sp, style]);
  let lastDate = "";
  return (
    <div className="wrap">
      <h2 style={{ marginTop: 10 }}>Next 72 hours</h2>
      <div className="filters">
        <select value={style} onChange={(e) => setStyle(e.target.value)} aria-label="Fishing style"><option value="any">Any style</option><option value="surf">Surf & headland</option><option value="estuary">Estuary & strait</option></select>
        <select value={loc} onChange={(e) => setLoc(e.target.value)} aria-label="Location"><option value="all">All locations</option>{data.locations.map((l) => <option key={l.id} value={l.id}>{l.short}</option>)}</select>
        <select value={sp} onChange={(e) => setSp(e.target.value)} aria-label="Species"><option value="all">All species</option>{data.species.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>
      </div>
      {rows.length === 0 && <p className="empty">Nothing matches. Widen the filters, or check the data status on Home.</p>}
      <ul className="rows">
        {rows.map(({ date, o }) => {
          const head = date !== lastDate; lastDate = date;
          return (
            <div key={date + o.location + o.species + o.window.start}>
              {head && <h3 style={{ margin: "16px 0 6px" }}>{fmtDate(date)}</h3>}
              <OppRow o={o} locName={locName} spName={spName} onRate={onRate} />
            </div>
          );
        })}
      </ul>
    </div>
  );
}
