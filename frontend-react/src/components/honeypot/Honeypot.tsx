import React, { useState, useEffect } from 'react';
import { fetchHandoffData, fetchDecoyRecords } from '../../services/api';
import { HandoffPayload } from '../../types';
import {
  Lock,
  Database,
  Search,
  RefreshCw,
  CheckCircle2,
  ChevronDown,
  Clock,
  Terminal,
} from 'lucide-react';

interface HoneypotProps {
  handoffToken?: string;
  onClearHandoff?: () => void;
}

export const Honeypot: React.FC<HoneypotProps> = ({ handoffToken }) => {
  const [handoff, setHandoff] = useState<HandoffPayload | null>(null);
  const [currentTable, setCurrentTable] = useState<string>('public_catalog');
  const [rows, setRows] = useState<Record<string, any>[]>([]);
  const [searchFilter, setSearchFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<Record<string, any> | null>(null);
  const [currentTime, setCurrentTime] = useState(new Date().toLocaleTimeString());

  // Clock tick
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date().toLocaleTimeString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Check URL search params for ?handoff=token or prop
  useEffect(() => {
    const token =
      handoffToken ||
      new URLSearchParams(window.location.search).get('handoff') ||
      sessionStorage.getItem('honeypotHandoffToken');

    if (token) {
      sessionStorage.setItem('honeypotHandoffToken', token);
      setLoading(true);
      fetchHandoffData(token)
        .then((data) => {
          setHandoff(data);
          if (data.rows && data.rows.length > 0) {
            setRows(data.rows);
            setCurrentTable(data.table || 'synthetic_records');
          }
        })
        .catch((err) => {
          console.warn('Handoff consumption fallback:', err);
          // Fallback to loading default records
          loadDataset('users');
        })
        .finally(() => setLoading(false));
    } else {
      loadDataset('users');
    }
  }, [handoffToken]);

  const loadDataset = async (dataset: string) => {
    setLoading(true);
    try {
      const data = await fetchDecoyRecords(dataset, true);
      if (data && data.rows) {
        setRows(data.rows);
        setCurrentTable(data.table || dataset);
      }
    } catch (err) {
      console.warn('Failed to load dataset:', err);
    } finally {
      setLoading(false);
    }
  };

  const isCanaryField = (key: string): boolean => {
    const lower = key.toLowerCase();
    return (
      lower.includes('token') ||
      lower.includes('secret') ||
      lower.includes('hash') ||
      lower.includes('signature') ||
      lower.includes('serial') ||
      lower.includes('routing')
    );
  };

  const filteredRows = rows.filter((r) =>
    Object.values(r).some((val) => String(val).toLowerCase().includes(searchFilter.toLowerCase()))
  );

  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans -m-6 flex flex-col md:flex-row">
      {/* Sidebar */}
      <aside className="w-full md:w-64 bg-slate-950 border-r border-slate-800/80 p-5 flex flex-col justify-between shrink-0">
        <div className="space-y-6">
          {/* Brand */}
          <div className="flex items-center gap-3">
            <span className="w-8 h-8 rounded-lg bg-teal-600 text-white font-bold flex items-center justify-center text-sm shadow-md shadow-teal-900/30">
              N
            </span>
            <div>
              <span className="font-bold text-sm tracking-tight text-white block">NORTHSTAR</span>
              <span className="text-[10px] text-slate-500 font-mono tracking-widest block uppercase">
                Enterprise Data Systems
              </span>
            </div>
          </div>

          {/* Node selector */}
          <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-teal-400" />
              <div className="leading-tight">
                <span className="font-semibold block text-slate-200">Operations Core</span>
                <span className="text-[10px] text-slate-500 font-mono">Node: cluster-prod-04</span>
              </div>
            </div>
            <ChevronDown className="w-4 h-4 text-slate-500" />
          </div>

          {/* Nav */}
          <div className="space-y-1">
            <span className="text-[10px] font-mono font-bold text-slate-500 tracking-wider uppercase px-2">
              WORKSPACE
            </span>
            <div className="space-y-1 pt-1">
              <button
                type="button"
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg bg-teal-950/60 text-teal-300 font-medium text-xs border border-teal-800/60"
              >
                <Database className="w-4 h-4 text-teal-400" />
                <span>Internal Data Explorer</span>
              </button>
              <button
                type="button"
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-900 text-xs transition-colors"
              >
                <Clock className="w-4 h-4 text-slate-500" />
                <span>Cluster Audit Trail</span>
              </button>
            </div>
          </div>
        </div>

        {/* Sidebar user status */}
        <div className="pt-6 border-t border-slate-800/80 space-y-3">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="font-mono text-[11px]">Internal Network Verified</span>
          </div>
          <div className="flex items-center gap-2.5 p-2 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
            <div className="w-7 h-7 rounded-full bg-slate-800 text-teal-400 font-bold flex items-center justify-center text-xs">
              JD
            </div>
            <div className="truncate leading-tight">
              <span className="font-semibold block text-slate-200">Jordan Davis</span>
              <span className="text-[10px] text-slate-500 font-mono">Systems administrator</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 p-6 md:p-8 space-y-6 overflow-x-hidden">
        {/* Top bar */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="text-xs text-slate-400 font-mono">
            Operations <span className="text-slate-600">/</span> Internal Data Hub
          </div>
          <div className="flex items-center gap-3 text-xs font-mono">
            <span className="px-2.5 py-1 rounded-full bg-teal-950/60 border border-teal-800/60 text-teal-300 text-[11px] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />
              SYSTEM: ONLINE &middot; US-EAST-01
            </span>
            <span className="text-slate-400">{currentTime}</span>
          </div>
        </div>

        {/* Authentic Enterprise Notice Banner */}
        <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-teal-400">
              <Lock className="w-4 h-4" />
            </div>
            <div>
              <span className="font-semibold text-xs text-slate-200 block">
                Northstar Enterprise Infrastructure &middot; Internal Data Service
              </span>
              <span className="text-[11px] text-slate-500 font-mono">
                Authorized Personnel Only &middot; Session Token Verified &middot; Node: cluster-prod-internal-04
              </span>
            </div>
          </div>
          <span className="text-[11px] font-mono text-emerald-400 px-2.5 py-1 rounded bg-emerald-950/60 border border-emerald-800/60">
            Active Session
          </span>
        </div>

        {/* Database Query Execution Card */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
              <Terminal className="w-4 h-4 text-teal-400" />
              <span>Database Query Execution</span>
            </div>
            <span className="text-[11px] font-mono text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> 200 OK &middot; EXECUTED
            </span>
          </div>

          <div className="p-3 rounded-lg bg-slate-900 font-mono text-xs text-emerald-300 border border-slate-800/80 overflow-x-auto">
            <code>
              {handoff?.query
                ? handoff.query.toLowerCase().startsWith('select')
                  ? handoff.query
                  : `SELECT * FROM ${currentTable} WHERE item = '${handoff.query.replace(/'/g, "''")}';`
                : `SELECT * FROM ${currentTable} ORDER BY id ASC LIMIT 50;`}
            </code>
          </div>
          <div className="text-[11px] text-slate-500 font-mono flex items-center justify-between">
            <span>Gateway Context: Internal Data Proxy (127.0.0.1)</span>
            <span>Query Runtime: 0.8ms</span>
          </div>
        </div>

        {/* Dataset Tabs */}
        <div className="space-y-2">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">
            AVAILABLE DATABASE TABLES &amp; VAULTS
          </span>
          <div className="flex items-center gap-2 flex-wrap">
            <button
              type="button"
              onClick={() => loadDataset('users')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                currentTable.includes('user')
                  ? 'bg-teal-600 text-white shadow-md shadow-teal-900/30'
                  : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              👤 Users &amp; Identities
            </button>
            <button
              type="button"
              onClick={() => loadDataset('financial')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                currentTable.includes('financ') || currentTable.includes('ledger')
                  ? 'bg-teal-600 text-white shadow-md shadow-teal-900/30'
                  : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              💳 Corporate Ledgers &amp; Accounts
            </button>
            <button
              type="button"
              onClick={() => loadDataset('secrets')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                currentTable.includes('secret')
                  ? 'bg-teal-600 text-white shadow-md shadow-teal-900/30'
                  : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              🔑 Cloud Infrastructure Secrets
            </button>
            <button
              type="button"
              onClick={() => loadDataset('catalog')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                currentTable.includes('catalog') || currentTable.includes('inventory')
                  ? 'bg-teal-600 text-white shadow-md shadow-teal-900/30'
                  : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              📦 Public Catalog &amp; Inventory
            </button>
          </div>
        </div>

        {/* Records Table Card */}
        <div className="border border-slate-800 rounded-xl bg-slate-950 overflow-hidden shadow-xl">
          {/* Table Tools */}
          <div className="p-3.5 border-b border-slate-800 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-200 uppercase tracking-wide">
                Table: {currentTable.replace('_', ' ')}
              </span>
              <span className="text-xs text-slate-500 font-mono">
                ({filteredRows.length} records retrieved)
              </span>
            </div>

            <div className="flex items-center gap-2">
              <div className="relative w-48">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
                <input
                  type="text"
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  placeholder="Filter records..."
                  className="w-full pl-7 pr-2.5 py-1.5 bg-slate-900 border border-slate-700/80 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-teal-500"
                />
              </div>

              <button
                type="button"
                onClick={() => loadDataset(currentTable)}
                title="Refresh table records"
                className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto max-h-[420px] overflow-y-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-slate-900/90 text-[11px] font-semibold text-slate-400 uppercase tracking-wider sticky top-0 border-b border-slate-800">
                <tr>
                  {columns.map((col) => (
                    <th key={col} className="px-4 py-2.5">
                      {col.replace('_', ' ')}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {filteredRows.map((row, idx) => (
                  <tr
                    key={idx}
                    onClick={() => setSelectedRecord(row)}
                    className="hover:bg-slate-900/70 cursor-pointer transition-colors"
                  >
                    {columns.map((col) => {
                      const val = String(row[col] ?? '');
                      const isCanary = isCanaryField(col);
                      return (
                        <td key={col} className="px-4 py-2.5 truncate max-w-xs">
                          {isCanary ? (
                            <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700/80 text-[11px] text-slate-200 font-mono">
                              {val}
                            </span>
                          ) : col === 'role' ? (
                            <span className="px-1.5 py-0.5 rounded bg-teal-950/60 text-teal-300 border border-teal-800/60 text-[11px]">
                              {val}
                            </span>
                          ) : (
                            val
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="px-4 py-2.5 border-t border-slate-800 bg-slate-900/40 flex items-center justify-between text-xs text-slate-500 font-mono">
            <span>Sync: Direct Internal Memory Pool</span>
            <span>Total: {rows.length} records</span>
          </div>
        </div>

        {/* Selected Record Drawer */}
        {selectedRecord && (
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-xs font-semibold text-slate-200">
                Record Inspector &middot; ID {selectedRecord.id || 'Selected'}
              </span>
              <button
                type="button"
                onClick={() => setSelectedRecord(null)}
                className="text-xs text-slate-400 hover:text-white"
              >
                &times; Close
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {Object.entries(selectedRecord).map(([k, v]) => (
                <div key={k} className="p-2.5 bg-slate-900/60 rounded-lg border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-mono">
                    {k.replace('_', ' ')}
                  </span>
                  <span className="text-xs font-mono text-slate-200 break-all">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
