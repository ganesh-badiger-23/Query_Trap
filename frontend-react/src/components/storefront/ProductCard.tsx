import React from 'react';
import { Product } from '../../types';
import { ShoppingBag, Star } from 'lucide-react';

interface ProductCardProps {
  product: Product;
  onAddToCart?: (product: Product) => void;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product, onAddToCart }) => {
  return (
    <div className="group bg-white rounded-xl border border-stone-200/90 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden flex flex-col">
      {/* Product Image placeholder with warm artisanal aesthetic */}
      <div className="h-44 bg-gradient-to-tr from-stone-100 via-stone-50 to-amber-50/50 flex items-center justify-center relative p-6 border-b border-stone-100">
        <span className="text-3xl filter drop-shadow-sm select-none">
          {product.category === 'Stationery'
            ? '📓'
            : product.category === 'Home'
            ? '💡'
            : product.category === 'Kitchen'
            ? '☕'
            : '🎒'}
        </span>
        <span className="absolute top-3 left-3 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-white/90 text-stone-600 border border-stone-200/80 shadow-xs uppercase tracking-wide">
          {product.category}
        </span>
      </div>

      {/* Card Details */}
      <div className="p-4 flex-1 flex flex-col justify-between space-y-3">
        <div>
          <div className="flex items-center gap-1 text-amber-500 text-[11px] mb-1">
            <Star className="w-3 h-3 fill-amber-400 stroke-amber-400" />
            <span className="font-medium text-stone-700">4.9</span>
            <span className="text-stone-400">(42 reviews)</span>
          </div>
          <h3 className="text-sm font-semibold text-stone-900 group-hover:text-amber-800 transition-colors">
            {product.item}
          </h3>
          <p className="text-xs text-stone-500 mt-1 line-clamp-2">
            {product.description || 'Artisanal workspace hardware crafted for enduring daily focus and tactile utility.'}
          </p>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-stone-100">
          <span className="text-base font-bold font-mono text-stone-900">
            ${Number(product.price).toFixed(2)}
          </span>
          <button
            type="button"
            onClick={() => onAddToCart?.(product)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-stone-900 hover:bg-stone-800 text-white text-xs font-medium shadow-xs transition-colors cursor-pointer"
          >
            <ShoppingBag className="w-3.5 h-3.5" />
            <span>Add to Cart</span>
          </button>
        </div>
      </div>
    </div>
  );
};
