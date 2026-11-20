import React from 'react';
import { GraduationCap, Sun, Moon } from 'lucide-react';
import { useTheme } from '../../hooks/useTheme';
import './Header.css';

export function Header() {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="header surface-overlay">
      <div className="app-container header__inner">
        <div className="header__brand">
          <div className="header__logo-badge">
            <GraduationCap size={22} />
          </div>
          <div className="header__brand-text">
            <div className="header__title-row">
              <h1 className="header__title type-h3">
                <span className="text-accent">Academic</span> Assignment Studio<span className="text-accent">.</span>
              </h1>
            </div>
            <p className="header__subtitle type-caption">
              Strict Word Boundaries • TrueType Typography • ReportLab Engine
            </p>
          </div>
        </div>

        <div className="header__actions">
          {/* Dark / Light Theme Toggle Switch */}
          <button
            type="button"
            className="theme-switch-btn"
            onClick={toggleTheme}
            aria-label="Toggle dark/light theme"
            title={`Switch to ${theme === 'dark' ? 'Light Mode (Pearl-Lavender)' : 'Dark Mode (Indigo-Violet)'}`}
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            <span className="theme-switch-label">{theme === 'dark' ? 'Light' : 'Dark'}</span>
          </button>
        </div>
      </div>
    </header>
  );
}
