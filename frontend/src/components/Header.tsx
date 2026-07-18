import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  BookOpen,
  Cpu,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  User,
  X,
} from 'lucide-react';

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/knowledge-base', label: 'Knowledge Base', icon: BookOpen },
  { to: '/settings', label: 'Settings', icon: Settings },
];

const Header: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
    setMobileMenuOpen(false);
  };

  return (
    <header className="app-header">
      <div className="header-shell">
        <NavLink to="/" className="brand-link" aria-label="ResolveAI dashboard">
          <span className="brand-mark">
            <Cpu size={19} />
          </span>
          <span className="brand-copy">
            <span className="brand-name">ResolveAI</span>
            <span className="brand-subtitle">Support operations</span>
          </span>
        </NavLink>

        {user ? (
          <>
            <nav className="header-desktop-nav" aria-label="Primary navigation">
              {navItems.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
                >
                  <Icon size={15} />
                  <span>{label}</span>
                </NavLink>
              ))}
            </nav>

            <div className="header-actions">
              <div className="user-chip" title={user.email}>
                <User size={14} />
                <span>{user.name || user.email}</span>
              </div>

              <button onClick={handleLogout} className="glass-btn glass-btn-secondary header-logout">
                <LogOut size={15} />
                <span>Log out</span>
              </button>
            </div>

            <button
              className="header-mobile-toggle"
              onClick={() => setMobileMenuOpen((open) => !open)}
              aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </>
        ) : (
          <div className="guest-status">
            <span className="status-dot" />
            <span>AI support ticket resolver</span>
          </div>
        )}
      </div>

      {user && mobileMenuOpen && (
        <div className="header-mobile-menu">
          <div className="mobile-user">
            <User size={14} />
            <span>{user.name || user.email}</span>
          </div>

          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setMobileMenuOpen(false)}
              className={({ isActive }) => `mobile-nav-link ${isActive ? 'mobile-nav-link-active' : ''}`}
            >
              <Icon size={15} />
              <span>{label}</span>
            </NavLink>
          ))}

          <button onClick={handleLogout} className="glass-btn glass-btn-danger mobile-logout">
            <LogOut size={15} />
            <span>Log out</span>
          </button>
        </div>
      )}
    </header>
  );
};

export default Header;
