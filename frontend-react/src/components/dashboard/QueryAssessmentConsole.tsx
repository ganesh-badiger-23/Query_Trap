import React, { useState } from 'react';
import { inspectQuery } from '../../services/api';
import { QueryResponse } from '../../types';
import { Send, Shield, AlertTriangle, ShieldCheck, Loader2 } from 'lucide-react';

interface QueryAssessmentConsoleProps {
  onQueryAnalyzed?: (res: QueryResponse) => void;
}

export const QueryAssessmentConsole: React.FC<QueryAssessmentConsoleProps> = ({ onQueryAnalyzed }) => {
  const [queryInput, setQueryInput] = useState('');
  const [siteContext, setSiteContext] = useState('Sentinel SOC Operations Console (:5100)');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryInput.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res = await inspectQuery({
        query: queryInput,
        site_context: siteContext,
      });
      setResult(res);
      onQueryAnalyzed?.(res);
    } catch (err: any) {
      setError(err.message || 'Inspection failed');
    } finally {
      setLoading(false);
    }
  };

  const setExample = (q: string) => {
    setQueryInput(q);
  };

  return (
    <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-lg backdrop-blur-sm space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-cyan-950/80 border border-cyan-800/80 text-cyan-400">
            <Shield className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Interactive Query Risk Analyzer</h3>
            <p className="text-xs text-slate-400">
              Evaluates AST anomalies, SQLi heuristics, and sensitivity before DB connection.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <span className="text-slate-500">Quick Test:</span>
          <button
            type="button"
            onClick={() => setExample('notebook')}
            className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-mono"
          >
            notebook (Safe)
          </button>
          <button
            type="button"
            onClick={() => setExample("' OR '1'='1")}
            className="px-2 py-0.5 rounded bg-rose-950/60 hover:bg-rose-900/60 text-rose-300 text-[11px] font-mono border border-rose-900/50"
          >
            ' OR '1'='1 (SQLi)
          </button>
          <button
            type="button"
            onClick={() => setExample('SELECT * FROM users')}
            className="px-2 py-0.5 rounded bg-amber-950/60 hover:bg-amber-900/60 text-amber-300 text-[11px] font-mono border border-amber-900/50"
          >
            SELECT * FROM users
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="md:col-span-2">
            <label className="block text-[11px] font-mono text-slate-400 mb-1">
              QUERY / RAW USER INPUT TO INSPECT
            </label>
            <div className="relative">
              <input
                type="text"
                value={queryInput}
                onChange={(e) => setQueryInput(e.target.value)}
                placeholder="e.g. SELECT * FROM users WHERE '1'='1' or search keywords..."
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 font-mono text-xs text-cyan-300 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-[11px] font-mono text-slate-400 mb-1">
              ORIGINATING CHANNEL / CONTEXT
            </label>
            <input
              type="text"
              value={siteContext}
              onChange={(e) => setSiteContext(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 font-mono text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        <div className="flex items-center justify-between pt-1">
          <span className="text-[11px] text-slate-500 font-mono">
            Threshold: &ge; 31 risk points triggers automatic honeypot diversion
          </span>
          <button
            type="submit"
            disabled={loading || !queryInput.trim()}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 text-white text-xs font-semibold shadow-md shadow-cyan-900/20 disabled:opacity-50 transition-all cursor-pointer"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            <span>{loading ? 'Inspecting AST…' : 'Inspect Query'}</span>
          </button>
        </div>
      </form>

      {error && (
        <div className="p-3 rounded-lg bg-rose-950/50 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {result && (
        <div
          className={`p-4 rounded-lg border text-xs space-y-2 animate-fade-in ${
            result.bucket === 'honeypot'
              ? 'bg-amber-950/20 border-amber-800/60 text-amber-200'
              : 'bg-emerald-950/20 border-emerald-800/60 text-emerald-200'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {result.bucket === 'honeypot' ? (
                <AlertTriangle className="w-4 h-4 text-amber-400" />
              ) : (
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              )}
              <span className="font-semibold text-sm">
                {result.bucket === 'honeypot'
                  ? 'SUSPICIOUS QUERY DIVERTED TO HONEYPOT'
                  : 'SAFE QUERY BOUND TO PRODUCTION CATALOG'}
              </span>
            </div>
            <div className="flex items-center gap-2 font-mono text-xs">
              <span>Risk: <b>{result.risk}/100</b> ({result.risk_band.toUpperCase()})</span>
              <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300">
                Route: {result.route}
              </span>
            </div>
          </div>
          <p className="text-slate-300 text-xs">{result.message}</p>
          {result.threats.length > 0 && (
            <div className="flex items-center gap-1.5 pt-1">
              <span className="text-[11px] text-slate-400">Threats:</span>
              {result.threats.map((t, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 rounded bg-rose-950/60 border border-rose-800 text-rose-300 font-mono text-[11px]"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
          {result.handoff && (
            <div className="font-mono text-[11px] text-slate-400 pt-1">
              Single-Use Handoff Token Issued:{' '}
              <code className="text-cyan-300 bg-slate-950 px-1.5 py-0.5 rounded">{result.handoff}</code>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
