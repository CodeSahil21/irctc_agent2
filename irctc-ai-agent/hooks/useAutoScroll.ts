"use client";

import { useEffect, useRef } from "react";

/**
 * Keeps a scroll container pinned to the bottom whenever `dep` changes,
 * unless the user has manually scrolled up to read history.
 */
export function useAutoScroll<T>(dep: T) {
  const containerRef = useRef<HTMLDivElement>(null);
  const isPinnedRef = useRef(true);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    function handleScroll() {
      if (!el) return;
      const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
      isPinnedRef.current = distanceFromBottom < 80;
    }

    el.addEventListener("scroll", handleScroll, { passive: true });
    return () => el.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || !isPinnedRef.current) return;
    el.scrollTop = el.scrollHeight;
  }, [dep]);

  return containerRef;
}
