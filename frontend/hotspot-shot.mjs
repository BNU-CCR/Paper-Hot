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
// Inspect the real WebGL canvas(es) inside the map container.
const probe = await page.evaluate(() => {
  const container = document.querySelector(".hotspot-network-canvas");
  const canvases = container ? container.querySelectorAll("canvas") : [];
  const info = {
    containerChildren: container ? container.childElementCount : 0,
    canvasCount: canvases.length,
    sizes: Array.from(canvases).map((c) => `${c.width}x${c.height}`),
  };
  // Non-uniformity heuristic: sample a grid across the canvas.
  try {
    const c = canvases[0];
    if (c) {
      const tmp = document.createElement("canvas");
      tmp.width = 32; tmp.height = 32;
      const ctx = tmp.getContext("2d");
      ctx.drawImage(c, 0, 0, 32, 32);
      const data = ctx.getImageData(0, 0, 32, 32).data;
      const distinct = new Set();
      for (let i = 0; i < data.length; i += 4) {
        distinct.add(`${data[i]},${data[i+1]},${data[i+2]}`);
        if (distinct.size > 12) break;
      }
      info.sampleDistinctColors = distinct.size;
      info.samplePixel = `${data[0]},${data[1]},${data[2]},${data[3]}`;
    }
  } catch (e) { info.sampleError = String(e); }
  return info;
});
console.log("canvas probe:", JSON.stringify(probe));
// Topic labels render as DOM elements in cosmograph's label layer.
const labelProbe = await page.evaluate(() => {
  const all = Array.from(document.querySelectorAll("*"));
  const withText = all
    .map((el) => el.childElementCount === 0 ? (el.textContent || "").trim() : "")
    .filter((t) => t && t.length > 2);
  return { labelLike: withText.filter((t) => /主题|模型|算法|平台|行动|传播|AI|媒体|网络|数据|信息|治理|广告|新闻|隐私|虚假/.test(t)).slice(0, 15), totalWithText: withText.length };
});
console.log("label probe:", JSON.stringify(labelProbe));

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
