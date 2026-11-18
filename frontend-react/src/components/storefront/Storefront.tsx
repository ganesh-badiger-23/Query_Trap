import React, { useState } from 'react';
import { Product } from '../../types';
import { HeroBanner } from './HeroBanner';
import { ProductCard } from './ProductCard';
import { inspectQuery } from '../../services/api';
import { ShoppingBag, ArrowLeft, Check } from 'lucide-react';

const INITIAL_PRODUCTS: Product[] = [
  { id: 1, item: 'Field notebook (Grid A5)', category: 'Stationery', price: 8.50, description: 'Smyth-sewn 80gsm fountain-pen friendly graph paper.' },
  { id: 2, item: 'Desk lamp (Architect V2)', category: 'Home', price: 24.00, description: 'Balanced arm with matte finish and dimmable 3000K LED.' },
  { id: 3, item: 'Travel mug (Thermal 16oz)', category: 'Kitchen', price: 16.25, description: 'Double-wall vacuum insulation preserving heat for 12 hours.' },
  { id: 4, item: 'Fountain pen (Solid Brass)', category: 'Stationery', price: 19.99, description: 'Engineered brass casing with smooth iridium nib.' },
  { id: 5, item: 'Canvas backpack (Rugged 24L)', category: 'Accessories', price: 48.00, description: 'Water-resistant waxed duck canvas with bridle leather straps.' },
  { id: 6, item: 'Ceramic planter (Minimalist)', category: 'Home', price: 14.50, description: 'Hand-thrown stoneware with built-in drainage saucer.' },
  { id: 7, item: 'Insulated water bottle (Steel)', category: 'Kitchen', price: 22.00, description: 'Food-grade stainless steel with leakproof sports cap.' },
  { id: 8, item: 'Mechanical pencil (0.5mm)', category: 'Stationery', price: 6.00, description: 'All-metal knurled grip mechanism for drafting precision.' },
];

interface StorefrontProps {
  onNavigateToHoneypot?: (handoffToken: string) => void;
}

export const Storefront: React.FC<StorefrontProps> = ({ onNavigateToHoneypot }) => {
  const [products, setProducts] = useState<Product[]>(INITIAL_PRODUCTS);
  const [activeCategory, setActiveCategory] = useState<string>('All');
  const [isSearching, setIsSearching] = useState(false);
  const [cartCount, setCartCount] = useState(0);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 2500);
  };

  const handleSearch = async (queryText: string) => {
    setIsSearching(true);
    try {
      const res = await inspectQuery({
        query: queryText,
        site_context: 'Harbor & Pine E-Commerce Storefront (:5200)',
        search_term: queryText,
      });

      // OpSec Rule: Transparent Honeypot Diversion
      // If the query was flagged as suspicious, transparently handoff to the Honeypot UI
      // without alerting the attacker or leaking security alerts!
      if (res.bucket === 'honeypot' && res.handoff) {
        if (onNavigateToHoneypot) {
          onNavigateToHoneypot(res.handoff);
          return;
        } else {
          // Direct native redirect fallback
          window.location.href = `http://127.0.0.1:5300/?handoff=${encodeURIComponent(res.handoff)}`;
          return;
        }
      }

      // Safe query: filter product items matching the returned rows or text
      if (res.rows && res.rows.length > 0) {
        const safeItems: Product[] = res.rows.map((r: any) => ({
          id: r.id || Math.floor(Math.random() * 1000),
          item: r.item || queryText,
          category: r.category || 'Stationery',
          price: Number(r.price) || 12.00,
          description: r.description || `Matching item for search "${queryText}".`,
        }));
        setProducts(safeItems);
      } else {
        const lower = queryText.toLowerCase();
        const filtered = INITIAL_PRODUCTS.filter(
          (p) => p.item.toLowerCase().includes(lower) || p.category.toLowerCase().includes(lower)
        );
        setProducts(filtered);
      }
    } catch (err: any) {
      console.warn('Storefront search fallback:', err);
      // Fallback local search
      const lower = queryText.toLowerCase();
      setProducts(INITIAL_PRODUCTS.filter((p) => p.item.toLowerCase().includes(lower)));
    } finally {
      setIsSearching(false);
    }
  };

  const handleAddToCart = (product: Product) => {
    setCartCount((c) => c + 1);
    showToast(`Added ${product.item} to cart`);
  };

  const filteredProducts =
    activeCategory === 'All'
      ? products
      : products.filter((p) => p.category.toLowerCase() === activeCategory.toLowerCase());

  const categories = ['All', 'Stationery', 'Home', 'Kitchen', 'Accessories'];

  return (
    <div className="min-h-screen bg-[#faf8f5] text-stone-900 font-sans -m-6 p-6">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-xl bg-stone-900 text-white text-xs font-medium shadow-xl flex items-center gap-2 animate-bounce">
          <Check className="w-4 h-4 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Top Navigation */}
      <header className="border-b border-stone-200 bg-white/80 backdrop-blur-md sticky top-0 z-30 mb-8 rounded-xl shadow-xs">
        <div className="max-w-6xl mx-auto px-4 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="w-8 h-8 rounded-lg bg-amber-800 text-amber-50 font-bold font-serif flex items-center justify-center text-base shadow-xs">
              H
            </span>
            <div>
              <span className="font-serif font-bold text-lg tracking-tight text-stone-900 block leading-tight">
                HARBOR &amp; PINE
              </span>
              <span className="text-[10px] tracking-widest uppercase text-stone-400 font-medium block">
                Artisanal Workspace Goods
              </span>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-6 text-xs font-medium text-stone-600">
            <a href="#catalog" className="text-amber-800 font-semibold">Catalog</a>
            <a href="#workspace" className="hover:text-stone-900 transition-colors">Workspace</a>
            <a href="#accessories" className="hover:text-stone-900 transition-colors">Leather &amp; Gear</a>
            <a href="#story" className="hover:text-stone-900 transition-colors">Studio Journal</a>
          </nav>

          <div className="flex items-center gap-3">
            <button
              type="button"
              className="relative p-2 rounded-xl bg-stone-100 hover:bg-stone-200 text-stone-700 transition-colors cursor-pointer"
            >
              <ShoppingBag className="w-4 h-4" />
              {cartCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-amber-800 text-white text-[10px] font-bold flex items-center justify-center">
                  {cartCount}
                </span>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Hero Section */}
        <HeroBanner onSearch={handleSearch} isLoading={isSearching} />

        {/* Category Filter Pills & Product Section */}
        <section id="catalog" className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-stone-200 pb-4">
            <div>
              <h2 className="text-xl font-bold font-serif text-stone-900">Featured Catalog</h2>
              <p className="text-xs text-stone-500">
                Displaying {filteredProducts.length} handcrafted essentials served live from production.db
              </p>
            </div>

            {/* Category Pills */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
              {categories.map((cat) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setActiveCategory(cat)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all cursor-pointer whitespace-nowrap ${
                    activeCategory === cat
                      ? 'bg-amber-800 text-white shadow-xs'
                      : 'bg-white border border-stone-200 text-stone-600 hover:bg-stone-100'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {/* Product Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
            {filteredProducts.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                onAddToCart={handleAddToCart}
              />
            ))}
          </div>

          {products.length !== INITIAL_PRODUCTS.length && (
            <div className="text-center pt-4">
              <button
                type="button"
                onClick={() => setProducts(INITIAL_PRODUCTS)}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-white border border-stone-300 text-stone-700 text-xs font-semibold hover:bg-stone-50 shadow-xs transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Reset to Full Catalog</span>
              </button>
            </div>
          )}
        </section>

        {/* Footer */}
        <footer className="pt-12 pb-6 border-t border-stone-200 text-center text-xs text-stone-500 space-y-2">
          <p className="font-serif font-bold text-stone-700 text-sm">HARBOR &amp; PINE WORKSPACE CO.</p>
          <p>Hand-built with genuine care &middot; Authentic e-commerce facade for Sentinel DB Active Defense</p>
          <p className="text-[11px] text-stone-400">&copy; 2026 Harbor &amp; Pine Inc. All rights reserved.</p>
        </footer>
      </div>
    </div>
  );
};
