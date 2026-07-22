"use client";

import { useEffect, useRef } from "react";

export function useAutoScroll<T>(dep: T) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const isPinnedRef = useRef(true);

  // Track whether the user has scrolled away from the bottom
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const handleScroll = () => {
      isPinnedRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    };

    el.addEventListener("scroll", handleScroll, { passive: true });
    return () => el.removeEventListener("scroll", handleScroll);
  }, []);

  // Scroll to bottom whenever dep changes, if pinned
  useEffect(() => {
    if (!isPinnedRef.current) return;
    sentinelRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [dep]);

  return { containerRef, sentinelRef };
}
