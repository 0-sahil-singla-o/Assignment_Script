import { useState, useEffect } from 'react';

export function useTheme() {
  const [theme, setTheme] = useState(() => {
    try {
      const saved = localStorage.getItem('theme');
      if (saved) return saved;
      return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches
        ? 'light'
        : 'dark';
    } catch {
      return 'dark';
    }
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem('theme', theme);
    } catch {}
    if (window.BgField && typeof window.BgField.setTheme === 'function') {
      window.BgField.setTheme(theme);
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  return { theme, toggleTheme, setTheme };
}
