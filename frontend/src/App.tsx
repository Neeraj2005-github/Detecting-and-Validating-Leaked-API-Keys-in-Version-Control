import { useMemo, useState } from 'react';
import { LayoutDashboard, ListFilter, ShieldCheck, Sparkles } from 'lucide-react';
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom';
import ProjectOverviewPage from './pages/ProjectOverviewPage';
import DashboardPage from './pages/DashboardPage';
import RepositoriesPage from './pages/RepositoriesPage';

const navItems = [
  { to: '/', label: 'Overview', icon: Sparkles },
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/repositories', label: 'Repositories', icon: ListFilter },
];

function AppLayout() {
  const [isDark] = useState(false);
  const shellClass = useMemo(() => `app-shell ${isDark ? 'theme-dark' : 'theme-light'}`, [isDark]);

  return (
    <div className={shellClass}>
      <header className="topbar">
        <div className="brand-block">
          <div className="brand-mark"><ShieldCheck size={15} /></div>
          <div className="brand-copy">
            <div className="brand-name">Detecting Secrets in Version Control</div>
            <div className="brand-subtitle">Secret History Detector</div>
          </div>
        </div>
      </header>

      <nav className="nav-bar" aria-label="Main navigation">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
            <Icon size={15} />
            {label}
          </NavLink>
        ))}
      </nav>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<ProjectOverviewPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/repositories" element={<RepositoriesPage />} />
          <Route path="/findings/:id" element={<ProjectOverviewPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}
