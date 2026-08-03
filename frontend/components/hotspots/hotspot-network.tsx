"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Cosmograph } from "@cosmograph/react";
import type { CosmographConfig } from "@cosmograph/react";
import type { GraphData, GraphPoint } from "../../types/hotspot";

/**
 * Hotspot semantic map rendered with Cosmograph (WebGL).
 *
 * Every analysis paper is a dot (fixed ~6px radius) colored by its topic
 * cluster and positioned by its UMAP coordinate. One topic anchor per shown
 * cloud sits at the centroid and carries the display label. Anchors encode the
 * current activity state: size = recent 30-day paper count, color = trend
 * direction (up/flat/down), shape = star (hot) vs diamond (emerging). Only
 * topics with recent_count >= 2 appear as anchors; inactive topics stay in
 * topics_meta. Positions are fixed (enableSimulation=false) so the UMAP layout
 * is preserved. Topic labels always render — the library's overlap culling is
 * disabled (see `showAllLabels`) so crowded clouds don't hide their names.
 * Clicking a topic (or a paper inside it) highlights the whole cloud and opens
 * the detail panel.
 */

const TOPIC_PALETTE = [
  "#4f8ff7", "#f28e2c", "#59a14f", "#e15759", "#76b7b2",
  "#edc949", "#af7aa1", "#ff9da7", "#9c755f", "#bab0ab",
  "#86bdf5", "#f6b26b", "#8fd18f", "#f1948a", "#a6d3cf",
  "#f5d76e", "#c39bd3", "#f4a7b9", "#b8a89a", "#d5d8dc",
];
const NOISE_COLOR = "#9aa0a6";
/** Topic anchor colors by trend direction (up / flat / down). */
const TREND_PALETTE: Record<string, string> = {
  up: "#4f9d5f",
  flat: "#9aa0a6",
  down: "#c9604a",
};

/**
 * The columns Cosmograph actually reads from each point/link object. Every
 * other field (paperId, paperCount, journalCount, growth, weight, …) is
 * dropped before upload — see `pickFields` and the note on `pointsData`.
 *
 * `size` and `trend` are written on EVERY point by the backend (papers carry
 * `size: 2.5`, `trend: ""`) — keeping both columns dense avoids sparse-column
 * SUMMARIZE crashes in Cosmograph's internal DuckDB.
 */
const POINT_FIELDS = ["id", "type", "topic", "topicId", "label", "heat", "size", "trend", "x", "y", "shape"];
const LINK_FIELDS = ["source", "target"];

/** Copy only the given fields out of `obj`, skipping any that are absent. */
function pickFields(obj: Record<string, unknown>, fields: readonly string[]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const field of fields) {
    if (field in obj) out[field] = obj[field];
  }
  return out;
}

function cssVar(name: string): string {
  if (typeof document === "undefined") return "#000";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#000";
}

/**
 * Screen-pixel shift to apply when focusing a topic, so the focused cloud
 * lands in the *visible* part of the map instead of behind the floating
 * detail panel: a right-side overlay on desktop, a bottom sheet on mobile.
 * Returns `[offsetX, offsetY]` — positive means move the focus left/up.
 */
function focusOffset(): [number, number] {
  const map = document.querySelector(".hotspot-map-area");
  const panel = document.querySelector(".hotspot-map-area .hotspot-detail-panel");
  if (!map || !panel) return [0, 0];
  const m = map.getBoundingClientRect();
  const p = panel.getBoundingClientRect();
  if (window.matchMedia("(max-width: 760px)").matches) {
    const visibleBottom = Math.min(m.bottom, p.top);
    return [0, (m.top + m.bottom) / 2 - (m.top + Math.max(m.top, visibleBottom)) / 2];
  }
  const visibleRight = Math.max(m.left, p.left);
  return [(m.left + m.right) / 2 - (m.left + visibleRight) / 2, 0];
}

/**
 * The cosmograph core keeps the d3-zoom engine under `_cosmos`. `zoomToPoint`
 * centers a point in the raw canvas; to offset that center (see focusOffset)
 * we build the same transform cosmograph would use and shift it before
 * applying. This is internal API — the plain `zoomToPoint` call is the
 * fallback if any of these internals go away.
 */
type CosmographInternals = {
  points?: { data?: { pointPositions?: Float32Array } };
  zoomInstance?: {
    getTransform: (
      positions: number[],
      scale?: number,
      padding?: number,
    ) => { k: number; x: number; y: number; translate: (dx: number, dy: number) => { k: number; x: number; y: number } };
    behavior: { transform: (selection: unknown, transform: unknown) => void };
  };
  canvasD3Selection?: {
    transition: () => {
      duration: (ms: number) => { call: (fn: (...args: unknown[]) => void, ...args: unknown[]) => unknown };
    };
  };
};

/**
 * Minimal shape of the library's `_internalApi`: the event bus a graph
 * rebuild dispatches `graphRebuilt` on, the status-message controls, and the
 * labels module — whose internal CSS-label renderer `showAllLabels` patches.
 */
type CosmographInternalApi = {
  addEventListener: (type: string, listener: () => void) => void;
  updateMessage: (message: string | null) => void;
  labels?: {
    render?: () => Promise<void>;
    _cssLabelsRenderer?: {
      draw?: (withIntersection?: boolean) => void;
      __labelsNoOverlap?: boolean;
    };
  };
};

/**
 * Cosmograph culls overlapping labels — its `LabelRenderer` keeps the
 * higher-weight label and hides the rest, so on a dense map several topic
 * labels silently disappear. The map is intentionally dense, so patch the
 * renderer's `draw` to always skip the intersection pass (`withIntersection:
 * false`): every label renders, and only off-screen ones hide. This reaches
 * library internals (`_internalApi.labels._cssLabelsRenderer`) the same way
 * `_cosmos` / `_internalApi` are used elsewhere in this file.
 */
function showAllLabels(inst: unknown): void {
  const labels = (inst as { _internalApi?: CosmographInternalApi })._internalApi?.labels;
  const renderer = labels?._cssLabelsRenderer;
  const draw = renderer?.draw;
  if (!renderer || !draw) return;
  if (renderer.__labelsNoOverlap) return; // this instance already patched
  renderer.__labelsNoOverlap = true;
  const originalDraw = draw.bind(renderer);
  renderer.draw = (withIntersection = true) => originalDraw(false);
  // Re-render now so labels hidden by an earlier culling pass come back.
  if (typeof labels.render === "function") {
    void labels.render().catch(() => {});
  }
}

interface HotspotNetworkProps {
  graph: GraphData;
  selectedNodeId: string | null;
  onSelectNode: (node: GraphPoint | null) => void;
}

export function HotspotNetwork({ graph, selectedNodeId, onSelectNode }: HotspotNetworkProps) {
  const cosmographRef = useRef<{
    selectPoints: (indices: number[] | null, addToSelection?: boolean) => void;
    unselectAllPoints: () => void;
    setFocusedPoint: (index?: number) => void;
    zoomToPoint: (index: number, duration?: number, scale?: number, canZoomOut?: boolean) => void;
    fitView: (duration?: number, padding?: number) => void;
  } | null>(null);
  const [mounted, setMounted] = useState(false);
  const onSelectRef = useRef(onSelectNode);
  onSelectRef.current = onSelectNode;

  const anchorIds = useMemo(
    () => graph.points.filter((p) => p.type === "topic").map((p) => p.id),
    [graph],
  );

  // Re-read theme colors when the `[data-theme]` attribute changes.
  // `themeReady` gates the first Cosmograph mount so the WebGL context is
  // created with the real theme colors instead of the hardcoded fallback —
  // otherwise a dark-theme user sees a white flash on first paint.
  const [themeVars, setThemeVars] = useState({ fg: "#111", card: "#fff" });
  const [themeReady, setThemeReady] = useState(false);
  useEffect(() => {
    const read = () =>
      setThemeVars({ fg: cssVar("--foreground"), card: cssVar("--card") });
    read();
    setThemeReady(true);
    const obs = new MutationObserver(read);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => obs.disconnect();
  }, []);

  // Cosmograph's built-in label chip ships a hardcoded dark background
  // (#24272fe0), which makes dark foreground text unreadable in light theme.
  // Override it with an inline style (a string containing ":" is applied as
  // the element's style attribute) built from the current theme tokens so
  // labels stay legible in both themes. Note: once pointLabelClassName is
  // set, pointLabelColor is ignored — the text color must live in the style.
  const labelStyle = useMemo(
    () =>
      `background: color-mix(in srgb, ${themeVars.card} 92%, transparent);` +
      ` color: ${themeVars.fg};` +
      " border-radius: 6px;" +
      " font-weight: 600 !important;" +
      " box-shadow: 0 1px 5px rgba(0,0,0,.22);",
    [themeVars],
  );

  // Feed the point/link objects straight into Cosmograph. The core ingests
  // them with its internal DuckDB instance and auto-generates the point/link
  // index columns, so the separate `usePreparedCosmographData` step (which
  // spun up a second, temporary DuckDB-WASM engine just to re-shape 300-ish
  // rows) is unnecessary — skipping it halves the WASM heap footprint and
  // drops the runtime CDN fetch.
  //
  // `pointIncludeColumns` / `linkIncludeColumns` are NOT honored in this
  // direct-feed path (they only gate columns in the data-kit
  // `prepareCosmographData` pipeline). Feeding the raw objects would upload
  // every field into the built-in DuckDB table, including the sparse numeric
  // columns `paperId` / `paperCount` / `journalCount` / `growth`. The
  // post-render `SUMMARIZE` step then throws `STDDEV_SAMP is out of range`
  // inside `_rebuildGraph`, and the library's error handler leaves its status
  // spinner stuck on top of the rendered map. Stripping the objects here is
  // what actually keeps those columns out — and keeps the DuckDB table (and
  // heap) small.
  const pointsData = useMemo(
    () => graph.points.map((p) => pickFields(p as unknown as Record<string, unknown>, POINT_FIELDS)),
    [graph],
  );
  const linksData = useMemo(
    () => graph.links.map((l) => pickFields(l as unknown as Record<string, unknown>, LINK_FIELDS)),
    [graph],
  );

  const mergedConfig = useMemo<CosmographConfig>(() => {
    return {
      points: pointsData,
      links: linksData,
      pointIdBy: "id",
      linkSourceBy: "source",
      linkTargetBy: "target",
      pointLabelBy: "label",
      // One color column for all points, but two visual meanings: paper dots
      // are colored by their topic cluster, while topic anchors are colored by
      // their trend direction (up/flat/down). `pointColorByFn` lets us branch
      // per point. NOTE: `pointColorStrategy`/`pointColorByMap` must NOT be set
      // — an explicit strategy makes Cosmograph ignore this function.
      pointColorBy: "topic",
      pointColorByFn: (value: number, index: number) => {
        const pt = graph.points[index];
        if (pt?.type === "topic") return TREND_PALETTE[pt.trend ?? "flat"] ?? NOISE_COLOR;
        if (value < 0) return NOISE_COLOR; // noise paper (not in any shown topic)
        return TOPIC_PALETTE[value % TOPIC_PALETTE.length];
      },
      // One size column for all points, but two visual meanings (same pattern
      // as pointColorByFn): providing `pointSizeByFn` runs Cosmograph in Direct
      // mode, so each branch returns an exact pixel radius. Paper dots get a
      // fixed, readable radius — the old `pointSizeRange` clamped them to ~3px,
      // which read as specks on a full-width map. Topic anchors keep the
      // backend's recent-count scale (already 9.6–16.8 in practice).
      pointSizeBy: "size",
      pointSizeByFn: (value: number, index: number) => {
        const pt = graph.points[index];
        if (pt?.type === "topic") {
          const v = Number(value) || 0;
          return Math.min(22, Math.max(9, v));
        }
        return 6; // paper dot radius (px)
      },
      pointShapeBy: "shape",
      pointXBy: "x",
      pointYBy: "y",
      pointClusterBy: "topic",
      enableSimulation: false,
      backgroundColor: themeVars.card,
      unknownColor: NOISE_COLOR,
      pointDefaultColor: NOISE_COLOR,
      pointGreyoutOpacity: 0.18,
      pointLabelClassName: labelStyle,
      hoveredPointLabelClassName: labelStyle,
      pointLabelFontSize: 14,
      pointLabelPosition: "center",
      showLabels: true,
      showLabelsFor: anchorIds,
      showTopLabels: false,
      showDynamicLabels: false,
      showHoveredPointLabel: true,
      showFocusedPointLabel: true,
      selectPointOnClick: false,
      focusPointOnClick: false,
      resetSelectionOnEmptyCanvasClick: true,
      fitViewDuration: 300,
      fitViewPadding: 0.12,
      // The cosmograph event manager forwards clicks to this callback with
      // `(pointIndex, position, event)`; pointIndex is undefined on empty
      // canvas clicks.
      onClick: (index?: number) => {
        if (typeof index !== "number") {
          // Click on empty space: clear the selection and zoom back out to
          // the whole semantic map (global view).
          onSelectRef.current(null);
          cosmographRef.current?.fitView(300, 0.12);
          return;
        }
        const pt = graph.points[index];
        if (!pt) return;
        if (pt.type === "topic") {
          onSelectRef.current(pt);
        } else {
          const anchor = graph.points.find((q) => q.type === "topic" && q.topicId === pt.topicId);
          onSelectRef.current(anchor ?? pt);
        }
      },
    } as CosmographConfig;
  }, [anchorIds, graph, pointsData, linksData, themeVars, labelStyle]);

  // Highlight the selected topic cloud (external selection or trend-table click).
  useEffect(() => {
    const inst = cosmographRef.current;
    if (!inst || !mounted) return;
    if (selectedNodeId) {
      const indices: number[] = [];
      let anchorIdx = -1;
      graph.points.forEach((p, i) => {
        if (p.topicId === selectedNodeId) {
          indices.push(i);
          if (p.type === "topic") anchorIdx = i;
        }
      });
      if (indices.length) inst.selectPoints(indices, false);
      if (anchorIdx >= 0) {
        inst.setFocusedPoint(anchorIdx);
        const [offsetX, offsetY] = focusOffset();
        const cosmos = (inst as unknown as { _cosmos?: CosmographInternals })._cosmos;
        const positions = cosmos?.points?.data?.pointPositions;
        const spaceX = positions?.[anchorIdx * 2];
        const spaceY = positions?.[anchorIdx * 2 + 1];
        const zoom = cosmos?.zoomInstance;
        const selection = cosmos?.canvasD3Selection;
        if (typeof spaceX === "number" && typeof spaceY === "number" && zoom && selection) {
          // Same transform cosmograph would build for zoomToPoint, shifted so
          // the focused topic centers in the part of the map the detail panel
          // doesn't cover.
          const base = zoom.getTransform([spaceX, spaceY], 3, 0.1);
          const shifted = base.translate(-offsetX / base.k, -offsetY / base.k);
          selection
            .transition()
            .duration(300)
            .call(zoom.behavior.transform, shifted);
        } else {
          inst.zoomToPoint(anchorIdx, 300);
        }
      }
    } else {
      inst.unselectAllPoints();
    }
  }, [selectedNodeId, graph, mounted]);

  if (!graph.points.length) {
    return (
      <div className="empty-state">
        <b>图谱数据暂未生成</b>
        <span>等待下一次自动更新构建热点网络。</span>
      </div>
    );
  }

  return (
    <div
      className={!themeReady ? "hotspot-network-canvas loading" : "hotspot-network-canvas"}
      style={{ width: "100%", height: "100%" }}
    >
      {!themeReady ? (
        <div className="empty-state">
          <b>图谱加载中…</b>
        </div>
      ) : (
        <Cosmograph
          onMount={(inst) => {
            cosmographRef.current = inst as typeof cosmographRef.current;
            setMounted(true);
            // Belt-and-suspenders: once a rebuild finishes, force the status
            // spinner hidden even if the library's own error handling left it
            // up (its non-`🚨` failure message keeps the spinner element).
            // This is a no-op on the happy path where it is already hidden.
            const internal = (inst as unknown as { _internalApi?: CosmographInternalApi })._internalApi;
            internal?.addEventListener("graphRebuilt", () => {
              internal.updateMessage(null);
              // The labels module (and its renderer) is re-created on every
              // rebuild, so re-apply the always-show patch to the fresh one.
              showAllLabels(inst);
            });
            // Patch now in case labels already exist on first mount; the
            // `graphRebuilt` listener re-patches after the initial build.
            showAllLabels(inst);
            // Fit the whole semantic map once the data table is uploaded.
            void inst
              .dataUploaded()
              .then(() => inst.fitView(0, 0.12))
              .catch(() => {});
          }}
          {...mergedConfig}
          style={{ width: "100%", height: "100%" }}
        />
      )}
    </div>
  );
}
