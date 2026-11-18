import React, { useState, useMemo } from 'react';
import { useSocketTelemetry } from '../../hooks/useSocketTelemetry';
import { TelemetryEvent, QueryResponse } from '../../types';
import { VirtualizedEventTable } from './VirtualizedEventTable';
import { RiskTimelineChart } from './RiskTimelineChart';
import { QueryAssessmentConsole } from './QueryAssessmentConsole';
import { EventDetailModal } from './EventDetailModal';
import {
  Shield,
  Activity,
  AlertOctagon,
  CheckCircle,
  Download,
  Trash2,
  Search,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  const { events, counts, isConnected, statusMessage, clearEvents, setEvents } = useSocketTelemetry();
  const [activeFilter, setActiveFilter] = useState<'all' | 'products' | 'attacks' | 'safe'>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedEvent, setSelectedEvent] = useState<TelemetryEvent | null>(null);

  // Apply filters and text search
  const filteredEvents = useMemo(() => {
    return events.filter((e) => {
      // 1. Category / Bucket filter
      if (activeFilter === 'products') {
        const isProduct =
          e.bucket === 'safe' ||
          (e.query_class && e.query_class.includes('Product')) ||
          (e.query_type && e.query_type.includes('Product'));
        if (!isProduct) return false;
      } else if (activeFilter === 'attacks') {
        if (e.bucket !== 'honeypot' && e.risk < 31) return false;
      } else if (activeFilter === 'safe') {
        if (e.risk > 30) return false;
      }

      // 2. Search keyword filter
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        const matchesQuery = e.query.toLowerCase().includes(term);
        const matchesIp = (e.ip || '').toLowerCase().includes(term);
        const matchesThreat = (e.threats || []).some((t) => t.toLowerCase().includes(term));
        if (!matchesQuery && !matchesIp && !matchesThreat) {
          return false;
        }
      }

      return true;
    });
  }, [events, activeFilter, searchTerm]);

  const handleExportJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(events, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `sentinel_telemetry_audit_${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleQueryAnalyzed = (res: QueryResponse) => {
    // If analyzed query from console, insert temporary telemetry record if not already emitted
    const syntheticEvent: TelemetryEvent = {
      id: `console-${Date.now()}`,
      timestamp: new Date().toISOString(),
      ip: '127.0.0.1',
      query: (res as any).query || 'Direct Query Test',
      threats: res.threats,
      risk: res.risk,
      risk_band: res.risk_band,
      route: res.route,
      bucket: res.bucket,
      site_context: res.site_context,
      table: res.table,
      action_taken: res.bucket === 'honeypot' ? '302 Diverted' : '200 Safe Lookup',
    };
    setEvents((prev) => [syntheticEvent, ...prev]);
  };

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-gradient-to-br from-cyan-500 to-teal-600 text-white shadow-lg shadow-cyan-900/30">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                Sentinel DB <span className="text-xs px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono">SOC Portal :5100</span>
              </h1>
              <p className="text-xs text-slate-400">
                Autonomous Database Deception, Active Defense &amp; Real-Time Telemetry Stream
              </p>
            </div>
          </div>
        </div>

        {/* Live stream badge */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs font-mono">
            <span
              className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'
              }`}
            />
            <span className={isConnected ? 'text-emerald-300' : 'text-rose-400'}>
              {isConnected ? 'LIVE WEBSOCKET STREAM' : 'DISCONNECTED'}
            </span>
          </div>

          <a
            href="http://127.0.0.1:5100/api/db/inspect?token=soc_token_live_2026"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors"
          >
            <span>DB Inspector API</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Safe Queries */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Safe In-Spec Lookups</span>
            <CheckCircle className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-cyan-400">{counts.safe}</div>
          <p className="text-[11px] text-slate-500 mt-1">Bound to production.db catalog</p>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-cyan-500/40" />
        </div>

        {/* Suspicious Traffic */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Suspicious Probes</span>
            <Activity className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-400">{counts.suspicious}</div>
          <p className="text-[11px] text-slate-500 mt-1">AST anomalies &amp; port reconnaissance</p>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-amber-500/40" />
        </div>

        {/* Honeypot Diversions */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Honeypot Diversions</span>
            <AlertOctagon className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-rose-400">{counts.honeypot}</div>
          <p className="text-[11px] text-slate-500 mt-1">Diverted to Northstar Honeypot (:5300)</p>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-rose-500/40" />
        </div>

        {/* Buffer Health / Virtualization stats */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>Buffer / Stream Status</span>
            <RefreshCw className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-100">{events.length}</div>
          <p className="text-[11px] text-emerald-400 truncate mt-1">{statusMessage}</p>
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-emerald-500/40" />
        </div>
      </div>

      {/* Upper Grid: Timeline Chart & Interactive Tester */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-6">
          <RiskTimelineChart events={events} />
        </div>
        <div className="lg:col-span-6">
          <QueryAssessmentConsole onQueryAnalyzed={handleQueryAnalyzed} />
        </div>
      </div>

      {/* Filter and Action Toolbar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-lg border border-slate-800">
        {/* Filters */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            type="button"
            onClick={() => setActiveFilter('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeFilter === 'all'
                ? 'bg-cyan-500 text-slate-950 font-semibold'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            All Events ({events.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter('products')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeFilter === 'products'
                ? 'bg-cyan-500 text-slate-950 font-semibold'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            🛍️ Product Searches
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter('attacks')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeFilter === 'attacks'
                ? 'bg-rose-500 text-slate-950 font-semibold'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            🚨 Attacks Diverted
          </button>
          <button
            type="button"
            onClick={() => setActiveFilter('safe')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeFilter === 'safe'
                ? 'bg-emerald-500 text-slate-950 font-semibold'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            Safe Only (&le; 30)
          </button>
        </div>

        {/* Search & Actions */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Filter by query, IP, threat..."
              className="w-full pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <button
            type="button"
            onClick={handleExportJson}
            title="Download JSON audit export"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
          >
            <Download className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={clearEvents}
            title="Clear current dashboard view"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Virtualized Event Table */}
      <VirtualizedEventTable
        events={filteredEvents}
        onSelectEvent={(evt) => setSelectedEvent(evt)}
      />

      {/* Modal Inspector */}
      <EventDetailModal
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
      />
    </div>
  );
};
