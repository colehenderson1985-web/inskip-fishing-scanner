import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import type { Latest, Location } from "../types";
import OppRow from "../components/OppRow";
import type { Opportunity } from "../types";

const STYLE = "https://tiles.openfreemap.org/styles/liberty";
const ZONE_COLOURS: Record<string, string> = { "Marine National Park": "#1b9e4b", "Conservation Park": "#e0b400", "Habitat Protection": "#1f4e8c", "General Use": "#7fb3d5" };

export default function MapPage({ data, dayIndex, locName, spName, selected, setSelected, onRate }:
  { data: Latest; dayIndex: number; locName: (id: string) => string; spName: (id: string) => string; selected: string | null; setSelected: (id: string | null) => void; onRate: (o: Opportunity) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markers = useRef<Record<string, maplibregl.Marker>>({});
  const [zones, setZones] = useState(true);
  const [wind, setWind] = useState(true);
  const day = data.days[dayIndex];

  useEffect(() => {
    if (!ref.current || mapRef.current) return;
    const [[s, w], [n, e]] = data.region.bbox;
    const map = new maplibregl.Map({ container: ref.current, style: STYLE, bounds: [[w, s], [e, n]], fitBoundsOptions: { padding: 30 }, attributionControl: false });
    map.addControl(new maplibregl.AttributionControl({ compact: true }));
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.addControl(new maplibregl.GeolocateControl({ positionOptions: { enableHighAccuracy: true }, trackUserLocation: false }), "bottom-right");
    map.on("load", async () => {
      try {
        const r = await fetch(`${import.meta.env.BASE_URL}data/cache/zones.geojson`);
        if (r.ok) {
          const gj = await r.json();
          map.addSource("zones", { type: "geojson", data: gj });
          map.addLayer({ id: "zones-fill", type: "fill", source: "zones", paint: {
            "fill-color": ["match", ["get", "zone_type"], "Marine National Park Zone", ZONE_COLOURS["Marine National Park"], "Conservation Park Zone", ZONE_COLOURS["Conservation Park"], "Habitat Protection Zone", ZONE_COLOURS["Habitat Protection"], ZONE_COLOURS["General Use"]],
            "fill-opacity": ["match", ["get", "zone_type"], "Marine National Park Zone", 0.45, "Conservation Park Zone", 0.3, 0.18] } });
          map.addLayer({ id: "zones-line", type: "line", source: "zones", paint: { "line-color": "#0b6e7a", "line-width": 1, "line-opacity": 0.5 } });
          map.on("click", "zones-fill", (ev) => {
            const f = ev.features?.[0]; if (!f) return;
            new maplibregl.Popup({ closeButton: true }).setLngLat(ev.lngLat).setHTML(`<b>${f.properties?.zone_name ?? ""}</b><br>${f.properties?.zone_type ?? ""} (${f.properties?.zone_id ?? ""})`).addTo(map);
          });
        }
      } catch { /* no zones file yet */ }
    });
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, []);

  useEffect(() => {
    const map = mapRef.current; if (!map) return;
    for (const m of Object.values(markers.current)) m.remove();
    markers.current = {};
    for (const loc of data.locations) {
      const ld = day.locations[loc.id];
      const el = document.createElement("div");
      el.className = `marker ${ld?.colour ?? "grey"} ${selected === loc.id ? "sel" : ""}`;
      el.textContent = ld?.score != null ? String(ld.score) : "–";
      el.title = loc.name;
      el.setAttribute("role", "button");
      el.onclick = () => setSelected(selected === loc.id ? null : loc.id);
      const m = new maplibregl.Marker({ element: el }).setLngLat([loc.centre[1], loc.centre[0]]).addTo(map);
      markers.current[loc.id] = m;
      if (wind && ld?.conditions?.wind_dir) {
        const dirDeg = compassToDeg(ld.conditions.wind_dir);
        const a = document.createElement("div");
        a.innerHTML = `<svg width="34" height="34" viewBox="-17 -17 34 34" style="transform:rotate(${dirDeg + 180}deg)"><path d="M0,-13 L5,-3 L1.5,-3 L1.5,13 L-1.5,13 L-1.5,-3 L-5,-3 Z" fill="#0f1c24" opacity=".75"/></svg>`;
        a.title = `${ld.conditions.wind_dir} ${ld.conditions.wind_kn} kn`;
        a.style.pointerEvents = "none";
        const wm = new maplibregl.Marker({ element: a, offset: [26, -14] }).setLngLat([loc.centre[1], loc.centre[0]]).addTo(map);
        markers.current[loc.id + "_w"] = wm;
      }
    }
  }, [data, dayIndex, selected, wind]);

  useEffect(() => {
    const map = mapRef.current; if (!map || !map.getLayer("zones-fill")) return;
    map.setLayoutProperty("zones-fill", "visibility", zones ? "visible" : "none");
    map.setLayoutProperty("zones-line", "visibility", zones ? "visible" : "none");
  }, [zones]);

  const loc = data.locations.find((l) => l.id === selected);
  const ld = loc ? day.locations[loc.id] : null;
  return (
    <>
      <div className="map" ref={ref} />
      <div className="map-legend">
        <span><i style={{ background: "var(--green)" }} />favourable</span>{" "}
        <span><i style={{ background: "var(--amber)" }} />mixed</span>{" "}
        <span><i style={{ background: "var(--red)" }} />poor</span>{" "}
        <span><i style={{ background: "var(--grey)" }} />no data</span>
        <div className="muted" style={{ fontSize: 11 }}>Pins are approximate access areas, not exact spots.</div>
        {zones && <div style={{ fontSize: 11, marginTop: 2 }}><i style={{ background: "#1b9e4b", borderRadius: 2 }} />no-take <i style={{ background: "#e0b400", borderRadius: 2 }} />2 lines <i style={{ background: "#1f4e8c", opacity: .5, borderRadius: 2 }} />habitat <i style={{ background: "#7fb3d5", borderRadius: 2 }} />general</div>}
      </div>
      <div className="map-toggles">
        <button className={zones ? "on" : ""} onClick={() => setZones(!zones)} aria-pressed={zones}>Marine park zones</button>
        <button className={wind ? "on" : ""} onClick={() => setWind(!wind)} aria-pressed={wind}>Wind arrows</button>
      </div>
      {loc && ld && <LocationSheet loc={loc} ld={ld} data={data} day={day} locName={locName} spName={spName} onClose={() => setSelected(null)} onRate={onRate} />}
    </>
  );
}

function compassToDeg(c: string): number {
  const pts = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
  const i = pts.indexOf(c); return i < 0 ? 0 : i * 22.5;
}

export function LocationSheet({ loc, ld, data, day, locName, spName, onClose, onRate }:
  { loc: Location; ld: Latest["days"][0]["locations"][string]; data: Latest; day: Latest["days"][0]; locName: (id: string) => string; spName: (id: string) => string; onClose: () => void; onRate: (o: Opportunity) => void }) {
  const opps = day.top.filter((o) => o.location === loc.id);
  const zone = data.rules.zones[loc.zone];
  const permit = loc.access.permit !== "none" ? data.rules.permits[loc.access.permit] : null;
  const share = async () => {
    const url = `${location.href.split("#")[0]}#/location/${loc.id}`;
    try { if (navigator.share) await navigator.share({ title: loc.name, text: `${loc.name}: ${ld.score ?? "–"}/100 today. ${ld.explain}`, url }); else { await navigator.clipboard.writeText(url); alert("Link copied"); } } catch { /* cancelled */ }
  };
  return (
    <div className="sheet" role="dialog" aria-label={loc.name}>
      <div className="grab" />
      <button className="close" onClick={onClose} aria-label="Close">×</button>
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
        <div className={`score ${ld.colour}`}>{ld.score ?? "–"}<small>{ld.colour === "grey" ? "no data" : ld.colour}</small></div>
        <div style={{ minWidth: 0 }}>
          <h3>{loc.name}</h3>
          <div className="small muted">{loc.access_point} · {loc.approx ? "approximate" : ""}</div>
          <div className="small" style={{ marginTop: 4 }}>
            <span className={`conf ${ld.confidence}`}>{ld.confidence} confidence</span>
            {ld.best_window && <> · best {ld.best_window.start}–{ld.best_window.end}</>}
          </div>
        </div>
      </div>
      <p style={{ marginTop: 10 }}>{ld.explain}</p>
      {ld.best_species.length > 0 && <p className="small">Target: {ld.best_species.map((s) => `${spName(s.species)} (${s.score})`).join(", ")}</p>}
      {ld.warnings.length > 0 && <div className="note warn">{ld.warnings.join(" · ")}</div>}
      <div className="note">
        <b>{zone?.name ?? loc.zone_name}</b> — {zone?.fishing === "prohibited" ? "no fishing" : `max ${loc.line_limit.lines} lines / ${loc.line_limit.hooks} hooks per person`}.
        {" "}Access: {loc.access.vehicle === "4wd" ? "4WD" : loc.access.vehicle}, {loc.access.tide_window}.
        {permit && <> <b>{permit.name}</b> required ({permit.cost}) — <a href={permit.buy} target="_blank" rel="noopener">buy</a>.</>}
        {" "}<a href={data.rules.zones_source} target="_blank" rel="noopener">zone rules</a>
      </div>
      {loc.hazards.length > 0 && <p className="small muted">Hazards: {loc.hazards.map((h) => h.replace(/_/g, " ")).join(", ")}. {loc.notes}</p>}
      {opps.length > 0 && <ul className="rows">{opps.map((o) => <OppRow key={o.species + o.window.start} o={o} locName={locName} spName={spName} showLocation={false} onRate={onRate} />)}</ul>}
      <p style={{ marginTop: 10 }}><button className="btn secondary" onClick={share}>Share this location</button></p>
    </div>
  );
}
