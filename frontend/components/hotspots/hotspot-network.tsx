"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Cosmograph } from "@cosmograph/react";
import type { CosmographConfig } from "@cosmograph/react";
import type { GraphData, GraphPoint } from "../../types/hotspot";

/**
 * Hotspot semantic map rendered with Cosmograph (WebGL).
 *
 * Every analysis paper is a small point colored by topic and positioned by its
 * UMAP coordinate; one star-shaped anchor per topic sits at the cloud centroid
 * and carries the display label. Positions are fixed (enableSimulation=false)
 * so the UMAP layout is preserved. Clicking a topic (or a paper inside it)
 * highlights the whole cloud and opens the detail panel.
 */

const TOPIC_PALETTE = [
  "#4f8ff7", "#f28e2c", "#59a14f", "#e15759", "#76b7b2",
  "#edc949", "#af7aa1", "#ff9da7", "#9c755f", "#bab0ab",
  "#86bdf5", "#f6b26b", "#8fd18f", "#f1948a", "#a6d3cf",
  "#f5d76e", "#c39bd3", "#f4a7b9", "#b8a89a", "#d5d8dc",
];
const NOISE_COLOR = "#9aa0a6";

function cssVar(name: string): string {
  if (typeof document === "undefined") return "#000";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#000";
}

function buildColorMap(points: GraphPoint[]): Record<string, string> {
  const map: Record<string, string> = {};
  const seen = new Set<number>();
  for (const p of points) {
    if (p.topic < 0 || seen.has(p.topic)) continue;
    seen.add(p.topic);
    map[String(p.topic)] = TOPIC_PALETTE[p.topic % TOPIC_PALETTE.length];
  }
  map["-1"] = NOISE_COLOR;
  return map;
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
  const colorMap = useMemo(() => buildColorMap(graph.points), [graph]);

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

  // Feed the raw point/link objects straight into Cosmograph. The core
  // ingests them with its internal DuckDB instance and auto-generates the
  // point/link index columns, so the separate `usePreparedCosmographData`
  // step (which spun up a second, temporary DuckDB-WASM engine just to
  // re-shape 300-ish rows) is unnecessary — skipping it halves the WASM
  // heap footprint and drops the runtime CDN fetch.
  //
  // Only upload the columns Cosmograph actually reads. Shipping every field
  // (`["*"]`) pulls in sparse numeric columns such as `paperId` / `growth`,
  // and the internal `SUMMARIZE` step then throws `STDDEV_SAMP is out of
  // range` inside `_rebuildGraph` — leaving its status spinner stuck on top
  // of the rendered map. Restricting the columns both fixes that and keeps
  // the DuckDB table (and heap) small.
  const mergedConfig = useMemo<CosmographConfig>(() => {
    return {
      points: graph.points as unknown as Record<string, unknown>[],
      links: graph.links as unknown as Record<string, unknown>[],
      pointIdBy: "id",
      linkSourceBy: "source",
      linkTargetBy: "target",
      pointLabelBy: "label",
      pointColorBy: "topic",
      pointColorStrategy: "map",
      pointColorByMap: colorMap,
      pointSizeBy: "heat",
      pointSizeRange: [3, 16],
      pointShapeBy: "shape",
      pointXBy: "x",
      pointYBy: "y",
      pointClusterBy: "topic",
      pointIncludeColumns: ["id", "type", "topic", "topicId", "label", "heat", "x", "y", "shape"],
      linkIncludeColumns: ["source", "target"],
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
  }, [colorMap, anchorIds, graph, themeVars, labelStyle]);

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
