import React, { useEffect, useRef } from 'react';

/**
 * Lightweight, Ultra-Low-CPU Dust Particle Background
 * Capped to DPR 1 and ~35 particles to ensure 0% system load and butter-smooth 60fps.
 */
export function BackgroundField() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const root = document.documentElement;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function token(name) {
      return getComputedStyle(root).getPropertyValue(name).trim();
    }

    function toRgb(value) {
      if (!value) return [255, 255, 255];
      if (value.charAt(0) === '#') {
        let h = value.slice(1);
        if (h.length === 3) h = h.split('').map((c) => c + c).join('');
        const n = parseInt(h, 16);
        return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
      }
      const m = value.match(/[\d.]+/g);
      return m && m.length >= 3 ? [+m[0], +m[1], +m[2]] : [255, 255, 255];
    }

    let pool = [];
    let w = 0;
    let h = 0;
    let parts = [];
    let raf = 0;
    let isVisible = true;

    function readTokens() {
      const colors = [1, 2, 3, 4, 5].map((i) => toRgb(token('--color-bg-dust-' + i)));
      pool = colors;
    }

    function build() {
      readTokens();
      // Keep DPR strictly at 1 for background particles to prevent 4K buffer GPU stalls
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = w;
      canvas.height = h;

      // Keep particles to a lightweight 30-40 count
      const n = Math.min(36, Math.max(18, Math.round((w * h) / 35000)));
      parts = [];
      for (let i = 0; i < n; i++) {
        parts.push({
          x: Math.random() * w,
          y: Math.random() * h,
          r: 0.6 + Math.random() * 1.2,
          v: 0.15 + Math.random() * 0.25,
          a: 0.25 + Math.random() * 0.45,
          c: pool[Math.floor(Math.random() * pool.length)] || [255, 255, 255]
        });
      }
    }

    function frame() {
      if (!isVisible || reduce) return;

      ctx.clearRect(0, 0, w, h);

      for (let i = 0; i < parts.length; i++) {
        const p = parts[i];
        p.y -= p.v;
        if (p.y < -4) {
          p.y = h + 4;
          p.x = Math.random() * w;
        }

        ctx.fillStyle = `rgba(${p.c[0]},${p.c[1]},${p.c[2]},${p.a})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, 6.2832);
        ctx.fill();
      }

      raf = requestAnimationFrame(frame);
    }

    build();
    if (!reduce) {
      raf = requestAnimationFrame(frame);
    }

    const handleResize = () => {
      build();
    };

    const handleVisibility = () => {
      if (document.hidden) {
        isVisible = false;
        cancelAnimationFrame(raf);
      } else {
        isVisible = true;
        if (!reduce) raf = requestAnimationFrame(frame);
      }
    };

    window.addEventListener('resize', handleResize);
    document.addEventListener('visibilitychange', handleVisibility);

    const observer = new MutationObserver(() => {
      readTokens();
    });
    observer.observe(root, { attributes: true, attributeFilter: ['data-theme', 'class'] });

    window.BgField = {
      pause: () => {
        isVisible = false;
        cancelAnimationFrame(raf);
      },
      resume: () => {
        if (reduce) return;
        isVisible = true;
        raf = requestAnimationFrame(frame);
      },
      refresh: () => {
        build();
      },
      setTheme: (mode) => {
        root.setAttribute('data-theme', mode === 'light' ? 'light' : 'dark');
        try {
          localStorage.setItem('theme', mode === 'light' ? 'light' : 'dark');
        } catch (e) {}
      }
    };

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', handleResize);
      document.removeEventListener('visibilitychange', handleVisibility);
      observer.disconnect();
    };
  }, []);

  return (
    <div className="bg-field" aria-hidden="true">
      <div className="bg-blob bg-blob-3" />
      <div className="bg-blob bg-blob-5" />
      <div className="bg-blob bg-blob-1" />
      <div className="bg-blob bg-blob-4" />
      <div className="bg-blob bg-blob-2" />
      <canvas ref={canvasRef} className="bg-dust" />
    </div>
  );
}
