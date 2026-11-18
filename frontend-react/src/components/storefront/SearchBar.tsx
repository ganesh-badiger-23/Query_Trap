import React, { useState } from 'react';
import { Search, Loader2 } from 'lucide-react';

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
  initialValue?: string;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  onSearch,
  isLoading = false,
  initialValue = '',
}) => {
  const [query, setQuery] = useState(initialValue);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-xl mx-auto relative">
      <div className="relative flex items-center shadow-lg shadow-stone-200/50 rounded-2xl overflow-hidden bg-white border border-stone-300 focus-within:border-amber-700 focus-within:ring-2 focus-within:ring-amber-700/20 transition-all">
        <div className="pl-4 text-stone-400">
          <Search className="w-5 h-5" />
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search goods, stationery, pens, notebooks..."
          className="w-full px-3.5 py-3.5 text-sm text-stone-800 placeholder-stone-400 bg-transparent focus:outline-none"
        />
        <div className="pr-2">
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="px-4 py-2 rounded-xl bg-amber-800 hover:bg-amber-900 text-white text-xs font-semibold shadow-xs disabled:opacity-50 transition-colors cursor-pointer flex items-center gap-1.5"
          >
            {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
            <span>Search</span>
          </button>
        </div>
      </div>
      <div className="flex items-center justify-center gap-2 mt-2.5 text-xs text-stone-500">
        <span className="font-medium">Trending:</span>
        <button
          type="button"
          onClick={() => {
            setQuery('notebook');
            onSearch('notebook');
          }}
          className="hover:text-amber-800 hover:underline cursor-pointer"
        >
          notebook
        </button>
        <span>&middot;</span>
        <button
          type="button"
          onClick={() => {
            setQuery('lamp');
            onSearch('lamp');
          }}
          className="hover:text-amber-800 hover:underline cursor-pointer"
        >
          desk lamp
        </button>
        <span>&middot;</span>
        <button
          type="button"
          onClick={() => {
            setQuery('mug');
            onSearch('mug');
          }}
          className="hover:text-amber-800 hover:underline cursor-pointer"
        >
          travel mug
        </button>
      </div>
    </form>
  );
};
