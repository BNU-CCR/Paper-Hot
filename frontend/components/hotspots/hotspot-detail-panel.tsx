"use client";

import { useEffect, useState } from "react";
import { X, ExternalLink, BookOpen, TrendingUp, Calendar } from "lucide-react";
import type { GraphNode, TopicDetail } from "../../types/hotspot";
import { publicDataUrl } from "../../lib/data-url";
import { Button } from "../ui/button";

interface HotspotDetailPanelProps {
  node: GraphNode | null;
  onClose: () => void;
}

function StatBadge({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="detail-stat">
      <span className="detail-stat-value">{value}</span>
      <span className="detail-stat-label">{label}</span>
    </div>
  );
}

export function HotspotDetailPanel({ node, onClose }: HotspotDetailPanelProps) {
  const [detail, setDetail] = useState<TopicDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!node?.detailFile) {
      setDetail(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError("");

    const url = publicDataUrl(`hotspots/${node.detailFile}`);
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: TopicDetail) => {
        if (!cancelled) setDetail(data);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [node?.detailFile]);

  if (!node) return null;

  const growthPercent = node.growth > 0 ? `+${Math.round(node.growth * 100)}%` : `${Math.round(node.growth * 100)}%`;
  const growthClass = node.growth > 0.3 ? "trend-up" : node.growth > 0 ? "trend-stable" : "trend-down";

  return (
    <aside className="hotspot-detail-panel">
      <div className="detail-header">
        <h2>{detail?.label || node.label}</h2>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="关闭详情">
          <X size={16} />
        </Button>
      </div>

      <div className="detail-stats">
        <StatBadge label="热度" value={node.hotScore} />
        <StatBadge label="环比" value={growthPercent} />
        <StatBadge label="论文" value={`${node.recentCount}/${node.paperCount}`} />
        <StatBadge label="期刊" value={node.journalCount} />
      </div>

      {loading && (
        <p className="detail-loading" role="status">加载主题详情…</p>
      )}

      {error && (
        <p className="detail-error">无法加载主题详情：{error}</p>
      )}

      {detail && !loading && (
        <>
          {detail.description && (
            <p className="detail-description">{detail.description}</p>
          )}

          {detail.why_hot && (
            <div className="detail-why-hot">
              <TrendingUp size={14} />
              <span>{detail.why_hot}</span>
            </div>
          )}

          {detail.keywords.length > 0 && (
            <div className="detail-keywords">
              {detail.keywords.map((kw) => (
                <span className="tag" key={kw}>{kw}</span>
              ))}
            </div>
          )}

          {detail.papers.length > 0 && (
            <div className="detail-papers">
              <h3>
                <BookOpen size={14} />
                代表论文
              </h3>
              <ul>
                {detail.papers.slice(0, 8).map((paper) => (
                  <li key={paper.id}>
                    <span className="detail-paper-title">{paper.title}</span>
                    <span className="detail-paper-meta">
                      <Calendar size={12} />
                      {paper.published_date || "日期未知"}
                      {paper.journal ? ` · ${paper.journal}` : ""}
                    </span>
                    {paper.summary && (
                      <span className="detail-paper-summary">{paper.summary}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </aside>
  );
}
