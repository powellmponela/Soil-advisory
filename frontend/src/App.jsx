// ---------------------------------------------------------------------------
// App.jsx – top-level shell with Advisory / Research tabs
// ---------------------------------------------------------------------------
import { useState } from 'react';
import './index.css';
import Advisory from './tabs/Advisory';
import Research from './tabs/Research';

const TABS = [
  { id: 'advisory',  label: 'Advisory' },
  { id: 'research',  label: 'Research' },
];

export default function App() {
  const [tab, setTab] = useState('advisory');

  return (
    <div className="app-shell">
      {/* ── Global header ── */}
      <header className="public-header">
        <div className="header-brand">
          <span className="kicker">NSAF Summer Maize · Western Nepal</span>
          <h1>Summer Maize Soil &amp; Nutrient Advisory</h1>
        </div>
        <nav className="header-tabs" aria-label="Main navigation">
          {TABS.map((t) => (
            <button
              key={t.id}
              id={`tab-${t.id}`}
              className={`tab-btn${tab === t.id ? ' active' : ''}`}
              onClick={() => setTab(t.id)}
              aria-current={tab === t.id ? 'page' : undefined}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      {/* ── Tab panels ── */}
      <main>
        {tab === 'advisory' && <Advisory />}
        {tab === 'research'  && <Research />}
      </main>

      <footer>
        Public interface: modelled supported pixels only · Research data and models remain restricted
      </footer>
    </div>
  );
}
