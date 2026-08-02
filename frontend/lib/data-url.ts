/**
 * Runtime (browser-safe) helper for building public data URLs,
 * accounting for the GitHub Pages basePath.
 *
 * Import this from client components — it does not touch node:fs.
 */

export function publicDataUrl(filePath: string): string {
  const base = process.env.NEXT_PUBLIC_BASE_PATH || "";
  const clean = filePath.replace(/^\/+/, "");
  return `${base}/data/${clean}`;
}
