"use client";

import { useEffect, useRef } from "react";

export function useAutoScroll<T>(dep: T) {
  const containerRef = useRef<HTMLDivElement>(null);
  const isPinnedRef = useRef(true);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const handleScroll = () => {
      if (!el) return;
      isPinnedRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    };

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
