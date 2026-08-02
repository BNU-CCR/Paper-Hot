"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Cosmograph, usePreparedCosmographData } from "@cosmograph/react";
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
  const [themeVars, setThemeVars] = useState({ fg: "#111", card: "#fff" });
  useEffect(() => {
    const read = () =>
      setThemeVars({ fg: cssVar("--foreground"), card: cssVar("--card") });
    read();
    const obs = new MutationObserver(read);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => obs.disconnect();
  }, []);

  // Prepare raw points/links into Cosmograph's internal format (async, once).
  const { config, isLoading, error } = usePreparedCosmographData(
    { points: { pointIdBy: "id" }, links: { linkSourceBy: "source", linkTargetsBy: ["target"] } },
    graph.points as unknown as Record<string, unknown>[],
    graph.links as unknown as Record<string, unknown>[],
  );

  const mergedConfig = useMemo<CosmographConfig>(() => {
    return {
      ...config,
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
      pointIncludeColumns: ["*"],
      enableSimulation: false,
      backgroundColor: themeVars.card,
      unknownColor: NOISE_COLOR,
      pointDefaultColor: NOISE_COLOR,
      pointGreyoutOpacity: 0.18,
      pointLabelColor: themeVars.fg,
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
          onSelectRef.current(null);
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
  }, [config, colorMap, anchorIds, graph, themeVars]);

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
        inst.zoomToPoint(anchorIdx, 300);
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

  if (error) {
    return (
      <div className="empty-state">
        <b>图谱渲染失败</b>
        <span>{String((error as Error).message || error)}</span>
      </div>
    );
  }

  return (
    <div className="hotspot-network-canvas" style={{ width: "100%", height: "100%", minHeight: 480 }}>
      {isLoading ? (
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
