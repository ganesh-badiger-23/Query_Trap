import React from 'react';
import { SearchBar } from './SearchBar';
import { Sparkles } from 'lucide-react';

interface HeroBannerProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

export const HeroBanner: React.FC<HeroBannerProps> = ({ onSearch, isLoading }) => {
  return (
    <section className="relative py-14 px-4 text-center bg-gradient-to-b from-stone-100 via-stone-50 to-stone-100/40 border-b border-stone-200/80 rounded-2xl overflow-hidden mb-10 shadow-xs">
      <div className="max-w-3xl mx-auto space-y-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-900 text-xs font-semibold tracking-wide">
          <Sparkles className="w-3.5 h-3.5 text-amber-700" />
          <span>AUTUMN 2026 WORKSPACE EDITION</span>
        </div>

        <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold text-stone-900 font-display tracking-tight leading-tight">
          Tools for Purposeful Focus &amp; Enduring Work.
        </h1>

        <p className="text-sm sm:text-base text-stone-600 max-w-xl mx-auto leading-relaxed">
          Heirloom-grade notebooks, brass pens, studio lighting, and field-tested accessories built to elevate your daily practice.
        </p>

        <div className="pt-2">
          <SearchBar onSearch={onSearch} isLoading={isLoading} />
        </div>
      </div>
    </section>
  );
};
