import { chromium } from "playwright";

const url = process.env.URL || "http://localhost:3000/hotspots/";
const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  headless: true,
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 400)); });
page.on("pageerror", (e) => errors.push("PAGEERROR: " + String(e.message).slice(0, 400)));
page.on("response", (r) => { if (r.status() >= 400) console.log("HTTP", r.status(), r.url()); });
page.on("requestfailed", (r) => console.log("REQFAIL", r.url(), r.failure()?.errorText));

await page.goto(url, { waitUntil: "networkidle", timeout: 60000 }).catch((e) => errors.push("NAV: " + e.message));
await page.waitForTimeout(5000);

const canvas = page.locator(".hotspot-network-canvas");
console.log("canvas count:", await canvas.count());
if (await canvas.count() > 0) {
  const box = await canvas.boundingBox();
  console.log("canvas box:", JSON.stringify(box));
  await canvas.screenshot({ path: "/tmp/hotspot-graph.png" });
}
await page.screenshot({ path: "/tmp/hotspot-page-full.png", fullPage: true });
await page.screenshot({ path: "/tmp/hotspot-surface.png", fullPage: true, fromSurface: false }).catch(() => {});
// also capture the graph container region via surface capture by clipping to it
try {
  const box = await canvas.boundingBox();
  if (box) await page.screenshot({ path: "/tmp/hotspot-surface-graph.png", clip: box, fromSurface: false });
} catch {}
// Try reading the WebGL canvas buffer directly (works only if preserveDrawingBuffer is on)
const glInfo = await page.evaluate(() => {
  const c = document.querySelector(".hotspot-network-canvas canvas");
  if (!c) return "no canvas";
  const gl = c.getContext("webgl2") || c.getContext("webgl");
  if (!gl) return "no gl";
  const px = new Uint8Array(4);
  gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
  return "readPixels " + Array.from(px).join(",");
});
console.log("gl probe:", glInfo);

console.log("graph tab:", await page.getByText("热点图谱", { exact: true }).count());
console.log("trend tab:", await page.getByText("趋势排行", { exact: true }).count());
console.log("empty state:", await page.getByText("图谱数据暂未生成", { exact: false }).count());

// WebGL capability probe on the same page
const webgl = await page.evaluate(() => {
  const c = document.createElement("canvas");
  const gl = c.getContext("webgl2") || c.getContext("webgl");
  return gl ? "OK " + (gl.getParameter(gl.VERSION) || "") : "UNAVAILABLE";
});
console.log("webgl:", webgl);

console.log("CONSOLE ERRORS:\n" + errors.join("\n"));
await browser.close();
