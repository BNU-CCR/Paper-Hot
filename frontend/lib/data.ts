import { readFileSync } from "node:fs";
import path from "node:path";
import type { HotspotsData, ManifestData, GraphData, TrendItem } from "../types/hotspot";
import type { Paper } from "../types/paper";

/**
 * Build-time readers for the static JSON snapshots in `public/data/`.
 *
 * The site is statically exported, so these run once at build time and the
 * result is pre-rendered into HTML — no runtime `fetch` in the browser.
 * Only import this module from server components (pages); pass the data
 * down to client components as props.
 */
const dataDir = path.join(process.cwd(), "public/data");

function readJson<T>(fileName: string, fallback: T): T {
  try {
    return JSON.parse(readFileSync(path.join(dataDir, fileName), "utf8")) as T;
  } catch {
    return fallback;
  }
}

export function getFeaturedPapers(): Paper[] {
  const data = readJson<unknown>("papers.json", []);
  return Array.isArray(data) ? (data as Paper[]) : [];
}

export function getAllPapers(): Paper[] {
  const data = readJson<unknown>("all_papers.json", []);
  return Array.isArray(data) ? (data as Paper[]) : [];
}

export function getHotspots(): HotspotsData {
  return readJson<HotspotsData>("hotspots.json", { topics: [] });
}

// ── Hotspot network data ──

/** Build-time: load the hotspot network graph. */
export function getHotspotGraph(): GraphData {
  return readJson<GraphData>("hotspots/graph.json", {
    schema_version: 0,
    generated_at: "",
    embedding_model: "",
    embedding_dimension: 0,
    nodes: [],
    edges: [],
  });
}

/** Build-time: load the hotspot manifest. */
export function getHotspotManifest(): ManifestData {
  return readJson<ManifestData>("hotspots/manifest.json", {
    schema_version: 0,
    generated_at: "",
    embedding_model: "",
    embedding_dimension: 0,
    period: { recent_start: "", recent_end: "", baseline_start: "", baseline_end: "" },
    paper_count: 0,
    topic_count: 0,
    edge_count: 0,
  });
}

/** Build-time: load the trend ranking. */
export function getHotspotTrends(): TrendItem[] {
  return readJson<TrendItem[]>("hotspots/trends.json", []);
}

/**
 * Runtime (browser) helper: build the URL for a public data file,
 * accounting for the GitHub Pages basePath.
 */
export function publicDataUrl(filePath: string): string {
  const base = process.env.NEXT_PUBLIC_BASE_PATH || "";
  const clean = filePath.replace(/^\/+/, "");
  return `${base}/data/${clean}`;
}
