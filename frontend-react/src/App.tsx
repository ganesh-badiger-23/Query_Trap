import React, { useState, useEffect } from 'react';
import { Dashboard } from './components/dashboard/Dashboard';
import { Storefront } from './components/storefront/Storefront';
import { Honeypot } from './components/honeypot/Honeypot';
import { Shield, ShoppingBag, Database } from 'lucide-react';

type ViewMode = 'dashboard' | 'storefront' | 'honeypot';

export const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewMode>('dashboard');
  const [activeHandoffToken, setActiveHandoffToken] = useState<string | undefined>(undefined);

  // Parse URL on initial load to handle direct routing
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const handoff = params.get('handoff');
    const viewParam = params.get('view') as ViewMode | null;

    if (handoff) {
      setActiveHandoffToken(handoff);
      setCurrentView('honeypot');
    } else if (viewParam && ['dashboard', 'storefront', 'honeypot'].includes(viewParam)) {
      setCurrentView(viewParam);
    } else if (window.location.port === '5200') {
      setCurrentView('storefront');
    } else if (window.location.port === '5300') {
      setCurrentView('honeypot');
    }
  }, []);

  const handleHoneypotDiversion = (handoffToken: string) => {
    setActiveHandoffToken(handoffToken);
    setCurrentView('honeypot');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Global View Switcher Topbar */}
      <header className="bg-slate-900/95 border-b border-slate-800/90 px-4 py-2.5 sticky top-0 z-50 backdrop-blur-md flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="font-bold text-sm tracking-tight text-white font-mono">
              SENTINEL DB &middot; REACT 18 SUITE
            </span>
          </div>
          <span className="hidden sm:inline-block text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 font-mono">
            Vite + TypeScript + Tailwind
          </span>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex items-center gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800">
          <button
            type="button"
            onClick={() => setCurrentView('dashboard')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              currentView === 'dashboard'
                ? 'bg-cyan-600 text-white shadow-sm shadow-cyan-900/40'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Shield className="w-3.5 h-3.5" />
            <span>SOC Telemetry (:5100)</span>
          </button>

          <button
            type="button"
            onClick={() => setCurrentView('storefront')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              currentView === 'storefront'
                ? 'bg-amber-800 text-white shadow-sm shadow-amber-900/40'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <ShoppingBag className="w-3.5 h-3.5" />
            <span>Storefront (:5200)</span>
          </button>

          <button
            type="button"
            onClick={() => setCurrentView('honeypot')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              currentView === 'honeypot'
                ? 'bg-teal-600 text-white shadow-sm shadow-teal-900/40'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>Honeypot (:5300)</span>
          </button>
        </div>
      </header>

      {/* Dynamic View Body */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto">
        {currentView === 'dashboard' && <Dashboard />}
        {currentView === 'storefront' && (
          <Storefront onNavigateToHoneypot={handleHoneypotDiversion} />
        )}
        {currentView === 'honeypot' && (
          <Honeypot handoffToken={activeHandoffToken} />
        )}
      </main>
    </div>
  );
};
