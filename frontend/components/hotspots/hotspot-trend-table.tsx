"use client";

import { TrendingDown, TrendingUp, Minus } from "lucide-react";
import type { TrendItem } from "../../types/hotspot";

interface HotspotTrendTableProps {
  trends: TrendItem[];
  onSelectTopic?: (topicId: string) => void;
}

function GrowthIcon({ growth }: { growth: number }) {
  if (growth > 0.15) return <TrendingUp size={14} className="icon-up" />;
  if (growth < -0.1) return <TrendingDown size={14} className="icon-down" />;
  return <Minus size={14} className="icon-stable" />;
}

function growthLabel(g: number): string {
  const pct = Math.round(g * 100);
  if (pct > 0) return `+${pct}%`;
  return `${pct}%`;
}

function ScoreBar({ score }: { score: number }) {
  return (
    <span className="score-bar-wrap">
      <span
        className="score-bar"
        style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
      />
    </span>
  );
}

export function HotspotTrendTable({ trends, onSelectTopic }: HotspotTrendTableProps) {
  if (!trends.length) {
    return (
      <div className="empty-state">
        <b>趋势数据暂未生成</b>
        <span>等待下一次自动更新构建趋势数据。</span>
      </div>
    );
  }

  const sorted = [...trends].sort((a, b) => b.hot_score - a.hot_score);

  return (
    <div className="trend-table-wrap">
      <table className="trend-table">
        <thead>
          <tr>
            <th className="col-rank">#</th>
            <th className="col-topic">研究主题</th>
            <th className="col-score">热度</th>
            <th className="col-growth">趋势</th>
            <th className="col-count">近期/总量</th>
            <th className="col-journals">期刊</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((item, idx) => (
            <tr
              key={item.topic_id}
              className={item.is_hot ? "row-hot" : ""}
              onClick={() => onSelectTopic?.(item.topic_id)}
              role={onSelectTopic ? "button" : undefined}
              tabIndex={onSelectTopic ? 0 : undefined}
              onKeyDown={(e) => {
                if (e.key === "Enter" && onSelectTopic) onSelectTopic(item.topic_id);
              }}
            >
              <td className="col-rank">{idx + 1}</td>
              <td className="col-topic">
                <span className="trend-topic-label">{item.label}</span>
                {item.lineage_status === "new" && (
                  <span className="badge-new">新</span>
                )}
              </td>
              <td className="col-score">
                <span className="score-value">{item.hot_score}</span>
                <ScoreBar score={item.hot_score} />
              </td>
              <td className="col-growth">
                <span className="growth-cell">
                  <GrowthIcon growth={item.growth} />
                  {growthLabel(item.growth)}
                </span>
              </td>
              <td className="col-count">
                {item.recent_count}<span className="count-total">/{item.baseline_count}</span>
              </td>
              <td className="col-journals">{item.journal_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
