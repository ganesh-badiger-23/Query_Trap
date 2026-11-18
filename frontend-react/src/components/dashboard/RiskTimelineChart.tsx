import React, { useMemo } from 'react';
import { TelemetryEvent } from '../../types';

interface RiskTimelineChartProps {
  events: TelemetryEvent[];
}

export const RiskTimelineChart: React.FC<RiskTimelineChartProps> = ({ events }) => {
  // Use the latest 30 events in chronological order for the timeline
  const points = useMemo(() => {
    const slice = [...events].slice(0, 30).reverse();
    return slice.map((e, idx) => ({
      index: idx,
      risk: e.risk,
      query: e.query,
      bucket: e.bucket,
      time: e.timestamp ? e.timestamp.split('T')[1]?.slice(0, 8) : '',
    }));
  }, [events]);

  if (points.length < 2) {
    return (
      <div className="h-40 flex items-center justify-center text-xs text-slate-500 border border-slate-800 rounded-lg bg-slate-900/40">
        Awaiting incoming telemetry query traffic to plot risk timeline…
      </div>
    );
  }

  const width = 600;
  const height = 140;
  const padding = 20;
  const innerWidth = width - padding * 2;
  const innerHeight = height - padding * 2;

  const getX = (i: number) => padding + (i / (points.length - 1)) * innerWidth;
  const getY = (risk: number) => padding + innerHeight - (Math.min(100, Math.max(0, risk)) / 100) * innerHeight;

  const pathD = points.reduce((acc, pt, i) => {
    const x = getX(i);
    const y = getY(pt.risk);
    return i === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
  }, '');

  const areaD = `${pathD} L ${getX(points.length - 1)} ${height - padding} L ${getX(0)} ${height - padding} Z`;

  return (
    <div className="w-full h-44 relative bg-slate-900/60 rounded-lg border border-slate-800/80 p-2 overflow-hidden flex flex-col justify-between">
      <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 px-1">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span>RISK TIMELINE (0-100)</span>
        </div>
        <div className="flex items-center gap-3 text-[10px]">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#38c9cf]"></span>Safe 0-30</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#e9ac55]"></span>Suspicious 31-69</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#eb6c7a]"></span>Critical 70-100</span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#eb6c7a] border-2 border-white"></span>Honeypot (302)</span>
        </div>
      </div>

      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-32 overflow-visible"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#38c9cf" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#38c9cf" stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Threshold indicator lines: 31 (Honeypot threshold) & 70 (Critical) */}
        <line
          x1={padding}
          y1={getY(31)}
          x2={width - padding}
          y2={getY(31)}
          stroke="#e9ac55"
          strokeDasharray="3 3"
          strokeWidth="1"
          opacity="0.4"
        />
        <line
          x1={padding}
          y1={getY(70)}
          x2={width - padding}
          y2={getY(70)}
          stroke="#eb6c7a"
          strokeDasharray="3 3"
          strokeWidth="1"
          opacity="0.4"
        />

        {/* Filled Area */}
        <path d={areaD} fill="url(#riskGradient)" />

        {/* Trend Line */}
        <path d={pathD} fill="none" stroke="#38c9cf" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

        {/* Data Points */}
        {points.map((pt, i) => {
          const isHoneypot = pt.bucket === 'honeypot';
          const color = pt.risk >= 70 ? '#eb6c7a' : pt.risk >= 31 ? '#e9ac55' : '#38c9cf';
          const r = isHoneypot ? 5.5 : 3.5;
          const strokeColor = isHoneypot ? '#ffffff' : '#0f172a';
          const strokeWidth = isHoneypot ? 2.5 : 1.5;

          return (
            <circle
              key={i}
              cx={getX(i)}
              cy={getY(pt.risk)}
              r={r}
              fill={color}
              stroke={strokeColor}
              strokeWidth={strokeWidth}
              className="transition-transform duration-150 hover:scale-125 cursor-pointer"
            >
              <title>
                {`[${pt.time}] Risk: ${pt.risk}/100 (${pt.risk >= 70 ? 'CRITICAL' : pt.risk >= 31 ? 'SUSPICIOUS' : 'SAFE'})\n` +
                 `Action: ${isHoneypot ? '🚨 HONEYPOT REDIRECTION (HTTP 302) -> honeypot.db / Canary Store' : '✅ Allowed (HTTP 200) -> production.db [Catalog]'}\n` +
                 `Query: ${pt.query}`}
              </title>
            </circle>
          );
        })}
      </svg>
    </div>
  );
};
