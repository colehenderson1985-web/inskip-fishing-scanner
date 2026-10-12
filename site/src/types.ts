export type Colour = "green" | "amber" | "red" | "grey";
export type Confidence = "high" | "medium" | "low" | "none";

export interface Window { start: string; end: string; label: string; start_iso: string; end_iso: string }

export interface Evidence {
  source: string | null; credit: string | null; date: string; catch_date: string | null;
  url: string | null; provenance: string; age_days: number; weight: number; excerpt: string;
}

export interface Conditions {
  wind_kn: number; gust_kn: number | null; wind_dir: string | null; wind_relation: string | null; effective_wind_kn: number | null;
  seas_m: number | null; swell_m: number | null; swell_period_s: number | null; sst_c: number | null;
  tide_stage: string | null; tide_range_m: number | null; tide_next: { t: string; h: number; type: "H" | "L" } | null;
  light: string; rain_24h_mm: number;
}

export interface Opportunity {
  rank?: number; location: string; species: string; window: Window; score: number; colour: Colour;
  confidence: Confidence; basis: string[]; factors: Record<string, number>; warnings: string[];
  conditions: Conditions; evidence: Evidence[]; explain: string;
  solunar?: { day_rating: string | null; major: string | null; minor: string | null };
}

export interface LocationDay {
  score: number | null; colour: Colour; confidence: Confidence;
  best_species: { species: string; score: number; window: Window }[];
  best_window?: Window; conditions?: Conditions; warnings: string[]; explain: string; evidence?: Evidence[];
}

export interface SolunarPeriod { kind: string; centre: string; start: string; end: string }
export interface Solunar {
  rating: "Best" | "Good" | "Fair" | "Poor"; base_rating: string; factor: number; days_from_new_or_full: number;
  moon_distance_km: number; distance_note: "perigee" | "apogee" | null; majors: SolunarPeriod[]; minors: SolunarPeriod[]; label: string;
}

export interface Astro {
  date: string; dawn: string; sunrise: string; sunset: string; dusk: string; moonrise: string | null; moonset: string | null;
  moon_phase_days: number; moon_illumination: number; moon_phase: string; near_new_or_full: boolean; solunar?: Solunar;
}

export interface Brief {
  outlook: string; headline: string; summary: string;
  best_location: { id: string; name: string; short: string; score: number } | null;
  best_species: { id: string; name: string } | null;
  windows: { location: string; species: string; start: string; end: string; score: number }[];
  drivers?: string[]; confidence: Confidence; warnings: string[];
}

export interface Day { date: string; brief: Brief; astro: Astro; top: Opportunity[]; locations: Record<string, LocationDay> }

export interface Location {
  id: string; name: string; short: string; type: string; centre: [number, number]; approx: boolean; access_point: string;
  aspect_deg: number; tide_ref: string; tide_note?: string; marine_point: string; zone: string; zone_name: string;
  line_limit: { lines: number; hooks: number }; access: { vehicle: string; permit: string; tide_window: string };
  hazards: string[]; species: string[]; notes: string;
}

export interface Species {
  id: string; name: string; short?: string; outlook: string; top_score: number | null; season: "peak" | "shoulder" | "off";
  season_months: { peak: number[]; shoulder?: number[] };
  best_locations: { location: string; name: string; score: number; window: Window; date: string }[];
  recent_reports: { source: string; date: string; catch_date: string | null; url: string | null; provenance: string; locations: string[]; excerpt: string }[];
  days_since_report: number | null; legal: { min_cm: number | null; max_cm?: number; possession: number; closures: string[] };
  legal_note?: string; closure_note?: string; closures: { name: string; active: boolean; source: string }[];
  techniques: string[]; confidence: Confidence | string; basis: string;
}

export interface Report {
  id: string; source: string; source_name: string; provenance: string; url: string | null; section: string;
  report_date: string; catch_date: string | null; catch_date_note: string; species: string[]; locations: string[];
  text: string; credit: string; rating?: number; kind?: string;
}

export interface Alert { id: string; title: string; summary: string; link: string; published: string | null; severity: string; locations: string[]; source: string }

export interface Tide { t: string; h: number; type: "H" | "L"; modelled?: boolean }

export interface Series { time: string[]; [k: string]: any }

export interface Health {
  generated_at: string; next_scheduled: string; overall: string; stale_categories: string[];
  sources: Record<string, { ok: boolean; last_success: string | null; items: number; error: string | null; category: string; stale?: boolean; note?: string }>;
}

export interface Latest {
  generated_at: string; timezone: string;
  region: { id: string; name: string; bbox: [number, number][]; marine_points: Record<string, { lat: number; lon: number; name: string }> };
  brief: Brief; days: Day[]; locations: Location[]; species: Species[]; reports: Report[];
  days_since_local_report: number | null; alerts: Alert[];
  bom: { coastal: any; obs: any[]; pressure_trend: string | null; marine_warning: boolean };
  tides: Record<string, Tide[]>; marine: Record<string, Series>; weather: Record<string, Series>;
  health: Health; rules: any; attribution: string[]; version: string;
}
