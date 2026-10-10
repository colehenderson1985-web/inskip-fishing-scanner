import { useState } from "react";
import type { Latest, Opportunity } from "../types";
import { REPO, todayISO, usePrefs } from "../data";

/** Settings + the Report Inbox and session rating. Submissions become GitHub issues
 *  (label "report") which the inbox workflow parses — no secrets in the browser. */
export default function SettingsPage({ data, prefill }: { data: Latest; prefill: Opportunity | null }) {
  const [prefs, setPrefs] = usePrefs();
  const inboxSources: { id: string; name: string }[] = (data as any).inbox_sources ?? [
    { id: "gardiners_fb", name: "Gardiners Tackle World Rainbow Beach (Facebook)" }, { id: "chandlery_fb", name: "The Chandlery Bait & Tackle, Tin Can Bay (Facebook)" },
    { id: "rb_charters_fb", name: "Rainbow Beach fishing charters (Facebook)" }, { id: "mate", name: "Friend / group message" }, { id: "own", name: "Own session" }, { id: "other", name: "Other" },
  ];
  const [src, setSrc] = useState(inboxSources[0].id);
  const [date, setDate] = useState(todayISO());
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [rLoc, setRLoc] = useState(prefill?.location ?? data.locations[0].id);
  const [rSp, setRSp] = useState(prefill?.species ?? "");
  const [rDate, setRDate] = useState(prefill ? prefill.window.start_iso.slice(0, 10) : todayISO());
  const [rating, setRating] = useState(0);
  const [rText, setRText] = useState("");

  const issueUrl = (title: string, payload: object) => {
    const body = "```json\n" + JSON.stringify(payload, null, 1) + "\n```\n\nSubmitted from the scanner. The inbox workflow will file this and close the issue.";
    return `${REPO}/issues/new?labels=report&title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
  };
  const reportUrl = issueUrl(`Report: ${inboxSources.find((s) => s.id === src)?.name ?? src} ${date}`, { kind: "report", source: src, post_date: date, text, url: url || undefined });
  const ratingUrl = issueUrl(`Rating: ${rLoc} ${rSp || ""} ${rDate} ${rating}/5`, { kind: "rating", source: "own", date: rDate, location: rLoc, species: rSp || undefined, rating, text: rText || undefined });

  return (
    <div className="wrap">
      <h2 style={{ marginTop: 10 }}>Settings</h2>
      <label>Display</label>
      <div className="filters">
        <button className={`btn ${prefs.theme === "day" ? "" : "secondary"}`} onClick={() => setPrefs({ ...prefs, theme: "day" })}>Daylight</button>
        <button className={`btn ${prefs.theme === "dawn" ? "" : "secondary"}`} onClick={() => setPrefs({ ...prefs, theme: "dawn" })}>Dawn (dark)</button>
      </div>

      <h2 id="report">Add a report</h2>
      <p className="small">Paste a shop's Facebook post, a mate's message, or your own notes. It's credited to the source, dated, and feeds the scanner on the next refresh. You'll be taken to GitHub to post it — sign in once, then it's one tap.</p>
      <label htmlFor="src">Source</label>
      <select id="src" value={src} onChange={(e) => setSrc(e.target.value)}>{inboxSources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>
      <label htmlFor="pdate">Post date</label>
      <input id="pdate" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      <label htmlFor="ptext">Text</label>
      <textarea id="ptext" value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste the report text here…" />
      <label htmlFor="purl">Link (optional)</label>
      <input id="purl" type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://" style={{ width: "100%" }} />
      <p style={{ marginTop: 12 }}><a className="btn" href={text.trim().length > 20 ? reportUrl : undefined} target="_blank" rel="noopener" aria-disabled={text.trim().length <= 20} style={text.trim().length <= 20 ? { opacity: .5, pointerEvents: "none" } : {}}>Submit report</a></p>

      <h2 id="rate">Rate a session</h2>
      <p className="small">One tap after you fish. This is what teaches the scanner which recommendations were any good.</p>
      <label htmlFor="rloc">Location</label>
      <select id="rloc" value={rLoc} onChange={(e) => setRLoc(e.target.value)}>{data.locations.map((l) => <option key={l.id} value={l.id}>{l.short}</option>)}</select>
      <label htmlFor="rsp">Species (optional)</label>
      <select id="rsp" value={rSp} onChange={(e) => setRSp(e.target.value)}><option value="">Any / mixed</option>{data.species.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>
      <label htmlFor="rdate">Date</label>
      <input id="rdate" type="date" value={rDate} onChange={(e) => setRDate(e.target.value)} />
      <label>How was it?</label>
      <div className="rating" role="radiogroup" aria-label="Rating 1 to 5">{[1, 2, 3, 4, 5].map((n) => <button key={n} className={rating === n ? "on" : ""} onClick={() => setRating(n)} role="radio" aria-checked={rating === n}>{n}</button>)}</div>
      <input type="text" value={rText} onChange={(e) => setRText(e.target.value)} placeholder="Optional: what you caught, bait, notes" style={{ width: "100%" }} />
      <p style={{ marginTop: 12 }}><a className="btn" href={rating ? ratingUrl : undefined} target="_blank" rel="noopener" style={!rating ? { opacity: .5, pointerEvents: "none" } : {}}>Submit rating</a></p>

      <h2>Admin</h2>
      <p className="small">
        <a href={`${REPO}/actions/workflows/refresh.yml`} target="_blank" rel="noopener">Run a manual refresh</a> (GitHub Actions → Run workflow) ·{" "}
        <a href={`${REPO}/issues?q=label%3Apipeline`} target="_blank" rel="noopener">pipeline issues</a> ·{" "}
        <a href={REPO} target="_blank" rel="noopener">source</a> · v{data.version}
      </p>

      <div className="foot">
        <p>Suitability scores combine tide stage, wind against each shore's aspect, swell, time of day, season, pressure, rain and dated public reports. They are not catch probabilities. Safety and legal restrictions always override a score. Check the <a href="https://www.qld.gov.au/recreation/activities/boating-fishing/rec-fishing/rules" target="_blank" rel="noopener">Queensland rules</a> and <a href="https://parks.qld.gov.au/park-alerts" target="_blank" rel="noopener">park alerts</a> before you go.</p>
        <p>{data.attribution.join(" · ")} · Map © OpenFreeMap, OpenMapTiles, OpenStreetMap contributors.</p>
        <p>All times AEST (Australia/Brisbane). Generated {data.generated_at}.</p>
      </div>
    </div>
  );
}
