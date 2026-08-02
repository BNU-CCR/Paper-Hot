"use client";

import { useEffect, useRef } from "react";
import type { GraphData, GraphNode } from "../../types/hotspot";

/** Read a CSS variable from the document root. */
function cssVar(name: string): string {
  if (typeof document === "undefined") return "#000";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#000";
}

function themeColors() {
  return {
    nodeColor: cssVar("--foreground"),
    nodeBg: cssVar("--background"),
    edgeColor: cssVar("--border"),
    accent: cssVar("--primary"),
    muted: cssVar("--muted-foreground"),
  };
}

interface HotspotNetworkProps {
  graph: GraphData;
  selectedNodeId: string | null;
  onSelectNode: (node: GraphNode | null) => void;
}

export function HotspotNetwork({ graph, selectedNodeId, onSelectNode }: HotspotNetworkProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<{
    sigma: { kill: () => void; refresh: () => void };
    graph: {
      getNodeAttributes: (id: string) => Record<string, unknown>;
      setNodeAttribute: (id: string, key: string, value: unknown) => void;
      forEachNode: (cb: (id: string) => void) => void;
    };
  } | null>(null);
  const onSelectRef = useRef(onSelectNode);
  onSelectRef.current = onSelectNode;

  // ── Initialize Sigma once ──────────────────────────────────────
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !graph.nodes.length) return;

    let cancelled = false;
    let resizeObserver: ResizeObserver | null = null;

    async function init() {
      const [Graph, Sigma] = await Promise.all([
        import("graphology").then((m) => m.default),
        import("sigma").then((m) => m.default),
      ]);

      if (cancelled || !container) return;

      const g = new Graph({ type: "undirected", multi: false, allowSelfLoops: false });
      const { nodeColor, nodeBg, edgeColor } = themeColors();

      for (const node of graph.nodes) {
        g.addNode(node.id, {
          x: node.x * 400,
          y: node.y * 400,
          size: node.size,
          label: node.label,
          color: nodeBg,
          borderColor: nodeColor,
          _data: node,
        });
      }

      for (const edge of graph.edges) {
        if (!g.hasNode(edge.source) || !g.hasNode(edge.target)) continue;
        g.addEdgeWithKey(edge.id, edge.source, edge.target, {
          size: Math.max(0.5, edge.width),
          color: edgeColor,
        });
      }

      const w = container.clientWidth || 800;
      const h = container.clientHeight || 600;
      const scale = Math.min(w, h) / 2.6;

      const sigma = new Sigma(g, container as HTMLElement, {
        renderEdgeLabels: false,
        labelRenderedSizeThreshold: 10,
        defaultEdgeType: "line",
        labelColor: { color: nodeColor },
        stagePadding: 40,
      });

      // Set initial camera to center the graph
      sigma.getCamera().setState({
        x: 0,
        y: 0,
        ratio: 1 / scale,
        angle: 0,
      });

      sigma.on("clickNode", ({ node }) => {
        const attrs = g.getNodeAttributes(node);
        const data = (attrs as Record<string, unknown>)._data as GraphNode | undefined;
        onSelectRef.current(data || null);
      });

      sigma.on("clickStage", () => {
        onSelectRef.current(null);
      });

      resizeObserver = new ResizeObserver(() => sigma.refresh());
      resizeObserver.observe(container as Element);

      instanceRef.current = { sigma, graph: g };
    }

    init();

    return () => {
      cancelled = true;
      resizeObserver?.disconnect();
      instanceRef.current?.sigma.kill();
      instanceRef.current = null;
    };
    // Only re-init when the graph data identity changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph]);

  // ── Update selection highlight ─────────────────────────────────
  useEffect(() => {
    const inst = instanceRef.current;
    if (!inst) return;

    const { nodeColor, nodeBg, accent } = themeColors();

    inst.graph.forEachNode((id: string) => {
      const isSelected = id === selectedNodeId;
      inst.graph.setNodeAttribute(id, "color", isSelected ? accent : nodeBg);
      inst.graph.setNodeAttribute(id, "borderColor", isSelected ? accent : nodeColor);
    });

    inst.sigma.refresh();
  }, [selectedNodeId]);

  // ── Theme change → refresh colors ──────────────────────────────
  useEffect(() => {
    const onThemeChange = () => {
      const inst = instanceRef.current;
      if (!inst) return;

      const { nodeColor, nodeBg, edgeColor, accent } = themeColors();
      const selected = selectedNodeId;

      inst.graph.forEachNode((id: string) => {
        const isSelected = id === selected;
        inst.graph.setNodeAttribute(id, "color", isSelected ? accent : nodeBg);
        inst.graph.setNodeAttribute(id, "borderColor", isSelected ? accent : nodeColor);
      });
      inst.sigma.refresh();
    };

    const observer = new MutationObserver(onThemeChange);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    return () => observer.disconnect();
  }, [selectedNodeId]);

  if (!graph.nodes.length) {
    return (
      <div className="empty-state">
        <b>图谱数据暂未生成</b>
        <span>等待下一次自动更新构建热点网络。</span>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="hotspot-network-canvas"
      style={{ width: "100%", height: "100%", minHeight: 480 }}
    />
  );
}
