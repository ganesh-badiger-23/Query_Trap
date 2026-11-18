import React, { useRef } from 'react';
import { TelemetryEvent } from '../../types';
import { useVirtualList } from '../../hooks/useVirtualList';
import { ShieldAlert, ShieldCheck, Database, Eye } from 'lucide-react';

interface VirtualizedEventTableProps {
  events: TelemetryEvent[];
  onSelectEvent: (event: TelemetryEvent) => void;
}

export const VirtualizedEventTable: React.FC<VirtualizedEventTableProps> = ({
  events,
  onSelectEvent,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const rowHeight = 56;

  const { totalHeight, virtualItems, totalCount } = useVirtualList({
    items: events,
    itemHeight: rowHeight,
    overscan: 8,
    containerRef,
  });

  const getClassificationBadge = (event: TelemetryEvent) => {
    const qClass = event.query_class || event.query_type || '';
    if (qClass.includes('Product Search') || event.bucket === 'safe') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-cyan-950/80 text-cyan-300 border border-cyan-800/60">
          🛍️ Product Search
        </span>
      );
    }
    if (qClass.includes('SQLi') || event.threats.some((t) => t.toLowerCase().includes('sqli'))) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-rose-950/80 text-rose-300 border border-rose-800/60">
          💉 SQLi Attempt
        </span>
      );
    }
    if (qClass.includes('Port') || event.threats.some((t) => t.toLowerCase().includes('port'))) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-amber-950/80 text-amber-300 border border-amber-800/60">
          🚨 Port Recon
        </span>
      );
    }
    if (event.threats.some((t) => t.toLowerCase().includes('xss'))) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-purple-950/80 text-purple-300 border border-purple-800/60">
          ⚠️ XSS Script
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-orange-950/80 text-orange-300 border border-orange-800/60">
        🛡️ Threat Diverted
      </span>
    );
  };

  const getRiskBadge = (risk: number) => {
    if (risk >= 70) {
      return (
        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-800">
          {risk} / 100
        </span>
      );
    }
    if (risk >= 31) {
      return (
        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800">
          {risk} / 100
        </span>
      );
    }
    return (
      <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
        {risk} / 100
      </span>
    );
  };

  if (events.length === 0) {
    return (
      <div className="py-20 text-center text-slate-500 border border-slate-800 rounded-lg bg-slate-900/40">
        <Database className="w-8 h-8 mx-auto mb-3 text-slate-600 opacity-60" />
        <p className="text-sm font-medium">No telemetry audit events match the current filter.</p>
        <p className="text-xs text-slate-600 mt-1">Execute queries on Storefront (:5200) to populate the live stream.</p>
      </div>
    );
  }

  return (
    <div className="border border-slate-800/90 rounded-lg bg-slate-900/70 overflow-hidden shadow-xl backdrop-blur-sm">
      {/* Virtualization Stats Header */}
      <div className="px-4 py-2 border-b border-slate-800/80 bg-slate-900/90 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>DOM VIRTUALIZATION ACTIVE</span>
        </div>
        <div className="font-mono text-[11px]">
          Rendering <span className="text-cyan-400 font-bold">{virtualItems.length}</span> of{' '}
          <span className="text-slate-200 font-bold">{totalCount}</span> buffered events (0% main-thread lag)
        </div>
      </div>

      {/* Table Header */}
      <div className="grid grid-cols-12 gap-3 px-4 py-3 border-b border-slate-800 bg-slate-950/60 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
        <div className="col-span-2">Classification</div>
        <div className="col-span-4">Query / Raw Payload</div>
        <div className="col-span-2">Threat Signatures</div>
        <div className="col-span-1 text-center">Risk Score</div>
        <div className="col-span-2">Isolation Target</div>
        <div className="col-span-1 text-right">Action</div>
      </div>

      {/* Virtualized Scrollable Viewport */}
      <div
        ref={containerRef}
        className="h-[460px] overflow-y-auto relative divide-y divide-slate-800/60 select-none scrollbar-thin scrollbar-thumb-slate-700"
      >
        <div style={{ height: `${totalHeight}px`, width: '100%', position: 'relative' }}>
          {virtualItems.map(({ item: event, offsetTop, index }) => (
            <div
              key={event.id || index}
              onClick={() => onSelectEvent(event)}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${rowHeight}px`,
                transform: `translateY(${offsetTop}px)`,
              }}
              className="grid grid-cols-12 gap-3 px-4 items-center hover:bg-slate-800/40 cursor-pointer transition-colors duration-100 text-xs border-b border-slate-800/40"
            >
              {/* Classification */}
              <div className="col-span-2 truncate flex items-center">
                {getClassificationBadge(event)}
              </div>

              {/* Query text */}
              <div className="col-span-4 truncate font-mono text-slate-200">
                <span title={event.query}>{event.query}</span>
              </div>

              {/* Threat tags */}
              <div className="col-span-2 truncate">
                {event.threats && event.threats.length > 0 ? (
                  <span className="text-[11px] text-rose-300 font-mono bg-rose-950/40 px-1.5 py-0.5 rounded border border-rose-900/60">
                    {event.threats[0]}
                  </span>
                ) : (
                  <span className="text-[11px] text-slate-500 font-mono">None (Safe)</span>
                )}
              </div>

              {/* Risk Score */}
              <div className="col-span-1 text-center">{getRiskBadge(event.risk)}</div>

              {/* Isolation Route Target */}
              <div className="col-span-2 truncate">
                {event.route === 'honeypot' || event.bucket === 'honeypot' ? (
                  <span className="inline-flex items-center gap-1.5 text-[11px] text-amber-300 bg-amber-950/50 px-2 py-0.5 rounded border border-amber-800/40">
                    <ShieldAlert className="w-3 h-3 text-amber-400" />
                    <span>honeypot.db (Decoy)</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 text-[11px] text-emerald-300 bg-emerald-950/50 px-2 py-0.5 rounded border border-emerald-800/40">
                    <ShieldCheck className="w-3 h-3 text-emerald-400" />
                    <span>production.db</span>
                  </span>
                )}
              </div>

              {/* Action */}
              <div className="col-span-1 text-right">
                <button
                  type="button"
                  className="p-1.5 rounded hover:bg-slate-700/60 text-slate-400 hover:text-cyan-300 transition-colors"
                  title="Inspect detailed audit payload"
                >
                  <Eye className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
