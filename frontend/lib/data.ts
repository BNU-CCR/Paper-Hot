import { readFileSync } from "node:fs";
import path from "node:path";
import type { HotspotsData } from "../types/hotspot";
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
