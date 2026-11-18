import React from 'react';
import { TelemetryEvent } from '../../types';
import { X, Shield, Terminal, Globe, Clock, Copy, Check } from 'lucide-react';

interface EventDetailModalProps {
  event: TelemetryEvent | null;
  onClose: () => void;
}

export const EventDetailModal: React.FC<EventDetailModalProps> = ({ event, onClose }) => {
  const [copied, setCopied] = React.useState(false);

  if (!event) return null;

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(event, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-700/80 rounded-xl shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/70">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-950/60 border border-cyan-800/60 text-cyan-400">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-100">SOC Audit Event Inspector</h2>
              <p className="text-xs text-slate-400 font-mono">Event ID: {event.id}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1">
                Risk Score
              </span>
              <span
                className={`text-lg font-bold font-mono ${
                  event.risk >= 70
                    ? 'text-rose-400'
                    : event.risk >= 31
                    ? 'text-amber-400'
                    : 'text-cyan-400'
                }`}
              >
                {event.risk} / 100
              </span>
            </div>
            <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1">
                Route Decision
              </span>
              <span
                className={`text-sm font-semibold ${
                  event.route === 'honeypot' ? 'text-amber-300' : 'text-emerald-300'
                }`}
              >
                {event.route === 'honeypot' ? '302 Honeypot Trap' : '200 Production DB'}
              </span>
            </div>
            <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1">
                Origin IP
              </span>
              <span className="text-sm font-mono text-slate-200">{event.ip || '127.0.0.1'}</span>
            </div>
          </div>

          {/* Raw Query Statement */}
          <div>
            <div className="flex items-center justify-between mb-1.5 text-xs text-slate-400 font-mono">
              <span className="flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-cyan-400" /> RAW QUERY STATEMENT
              </span>
            </div>
            <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/90 font-mono text-xs text-emerald-300 overflow-x-auto whitespace-pre-wrap break-all">
              {event.query}
            </div>
          </div>

          {/* Threat Signatures */}
          <div>
            <span className="text-xs text-slate-400 font-mono block mb-1.5">THREAT SIGNATURES DETECTED</span>
            <div className="flex flex-wrap gap-2">
              {event.threats && event.threats.length > 0 ? (
                event.threats.map((threat, idx) => (
                  <span
                    key={idx}
                    className="px-2.5 py-1 rounded bg-rose-950/60 border border-rose-800/80 text-rose-300 font-mono text-xs"
                  >
                    ⚠️ {threat}
                  </span>
                ))
              ) : (
                <span className="text-xs text-slate-500 font-mono">No threat signatures detected (Safe catalog query)</span>
              )}
            </div>
          </div>

          {/* Context & Metadata */}
          <div className="space-y-2 text-xs">
            <div className="flex items-start gap-2 text-slate-300">
              <Globe className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
              <div>
                <span className="text-slate-500 block text-[10px]">Site Context / Gateway Channel</span>
                <span className="font-mono">{event.site_context || 'Direct HTTP Gateway / API Call'}</span>
              </div>
            </div>
            <div className="flex items-start gap-2 text-slate-300">
              <Clock className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
              <div>
                <span className="text-slate-500 block text-[10px]">Audit Timestamp (ISO 8601 UTC)</span>
                <span className="font-mono">{event.timestamp}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t border-slate-800 bg-slate-950/70">
          <button
            onClick={handleCopyJson}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied JSON!' : 'Copy Event JSON'}</span>
          </button>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded text-xs font-medium bg-cyan-600 hover:bg-cyan-500 text-white transition-colors"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
