"use client";

import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

interface UseScrollRevealOptions {
  y?: number;
  duration?: number;
  stagger?: number;
  start?: string;
  once?: boolean;
}

export function useScrollReveal<T extends HTMLElement>(options: UseScrollRevealOptions = {}) {
  const ref = useRef<T>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const ctx = gsap.context(() => {
      gsap.from(el.querySelectorAll("[data-reveal]"), {
        y: options.y ?? 40,
        opacity: 0,
        duration: options.duration ?? 0.8,
        stagger: options.stagger ?? 0.1,
        ease: "expo.out",
        scrollTrigger: {
          trigger: el,
          start: options.start ?? "top 85%",
          once: options.once ?? true,
        },
      });
    }, el);

    return () => ctx.revert();
  }, [options.y, options.duration, options.stagger, options.start, options.once]);

  return ref;
}

export function useParallax<T extends HTMLElement>(speed: number = 0.5) {
  const ref = useRef<T>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const ctx = gsap.context(() => {
      gsap.to(el, {
        y: () => -100 * speed,
        ease: "none",
        scrollTrigger: {
          trigger: el,
          start: "top bottom",
          end: "bottom top",
          scrub: true,
        },
      });
    }, el);

    return () => ctx.revert();
  }, [speed]);

  return ref;
}

export function useHorizontalScroll<T extends HTMLElement>() {
  const ref = useRef<T>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const panels = el.querySelectorAll<HTMLElement>("[data-panel]");
    const totalWidth = Array.from(panels).reduce((acc, p) => acc + p.offsetWidth, 0);

    const ctx = gsap.context(() => {
      gsap.to(panels, {
        x: () => -(totalWidth - window.innerWidth),
        ease: "none",
        scrollTrigger: {
          trigger: el,
          pin: true,
          scrub: 1,
          end: () => `+=${totalWidth}`,
          invalidateOnRefresh: true,
        },
      });
    }, el);

    return () => ctx.revert();
  }, []);

  return ref;
}