import { useState, useEffect, RefObject } from 'react';

interface UseVirtualListOptions<T> {
  items: T[];
  itemHeight?: number;
  overscan?: number;
  containerRef: RefObject<HTMLElement | null>;
}

export interface VirtualRow<T> {
  index: number;
  item: T;
  offsetTop: number;
}

export function useVirtualList<T>({
  items,
  itemHeight = 52,
  overscan = 6,
  containerRef,
}: UseVirtualListOptions<T>) {
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(500);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const handleScroll = () => {
      setScrollTop(el.scrollTop);
    };

    const handleResize = () => {
      if (el.clientHeight) {
        setContainerHeight(el.clientHeight);
      }
    };

    handleResize();
    el.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', handleResize);

    return () => {
      el.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', handleResize);
    };
  }, [containerRef]);

  const totalHeight = items.length * itemHeight;
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const endIndex = Math.min(
    items.length - 1,
    Math.floor((scrollTop + containerHeight) / itemHeight) + overscan
  );

  const virtualItems: VirtualRow<T>[] = [];
  if (items.length > 0) {
    for (let i = startIndex; i <= endIndex; i++) {
      if (items[i] !== undefined) {
        virtualItems.push({
          index: i,
          item: items[i],
          offsetTop: i * itemHeight,
        });
      }
    }
  }

  return {
    totalHeight,
    virtualItems,
    startIndex,
    endIndex,
    renderedCount: virtualItems.length,
    totalCount: items.length,
  };
}
