import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogOut, Layout, Cpu, User, Settings, Menu, X, BookOpen } from 'lucide-react';

const Header: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
    setMobileMenuOpen(false);
  };

  const navLinkStyle = ({ isActive }: { isActive: boolean }) => ({
    padding: '0.45rem 0.85rem',
    fontSize: '0.8rem',
    display: 'flex',
    alignItems: 'center',
    gap: '0.35rem',
    borderRadius: '8px',
    border: `1px solid ${isActive ? 'var(--color-primary)' : 'var(--border-color)'}`,
    background: isActive ? 'rgba(99,102,241,0.15)' : 'rgba(255,255,255,0.04)',
    color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
    textDecoration: 'none',
    transition: 'all 0.2s ease',
    cursor: 'pointer',
  });

  return (
    <header style={{
      borderBottom: '1px solid var(--border-color)',
      background: 'rgba(6, 8, 20, 0.4)',
      backdropFilter: 'blur(10px)',
      position: 'sticky',
      top: 0,
      zIndex: 10
    }}>
      <div style={{
        maxWidth: '1200px',
        margin: '0 auto',
        padding: '1rem 1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        {/* Logo */}
        <NavLink
          to="/"
          style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', textDecoration: 'none' }}
        >
          <div style={{
            background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%)',
            padding: '0.5rem',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 15px rgba(99, 102, 241, 0.3)'
          }}>
            <Cpu size={20} color="#fff" />
          </div>
          <span style={{
            fontFamily: 'var(--font-title)',
            fontSize: '1.4rem',
            fontWeight: 700,
            background: 'linear-gradient(to right, #ffffff, #c7d2fe)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>
            ResolveAI
          </span>
        </NavLink>

        {/* Desktop Nav */}
        {user ? (
          <div className="header-desktop-nav" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <NavLink to="/" style={navLinkStyle} end>
              <Layout size={14} />
              <span>Dashboard</span>
            </NavLink>

            <NavLink to="/knowledge-base" style={navLinkStyle}>
              <BookOpen size={14} />
              <span>Knowledge Base</span>
            </NavLink>

            <NavLink to="/settings" style={navLinkStyle}>
              <Settings size={14} />
              <span>Settings</span>
            </NavLink>

            <div style={{
              width: '1px',
              height: '24px',
              background: 'var(--border-color)',
              margin: '0 0.25rem'
            }} />

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>
              <User size={14} />
              <span>{user.name || user.email}</span>
            </div>

            <button
              onClick={handleLogout}
              className="glass-btn glass-btn-secondary"
              style={{ padding: '0.45rem 0.85rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
            >
              <LogOut size={14} />
              <span>Log out</span>
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>
            <Layout size={16} />
            <span>AI Support Ticket Resolver</span>
          </div>
        )}

        {/* Mobile Hamburger */}
        {user && (
          <button
            className="header-mobile-toggle"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            style={{
              display: 'none',
              background: 'none',
              border: 'none',
              color: 'var(--color-text-main)',
              cursor: 'pointer',
              padding: '0.25rem'
            }}
          >
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        )}
      </div>

      {/* Mobile Menu Dropdown */}
      {user && mobileMenuOpen && (
        <div className="header-mobile-menu" style={{
          padding: '0.75rem 1.5rem 1.25rem',
          display: 'none',
          flexDirection: 'column',
          gap: '0.5rem',
          borderTop: '1px solid var(--border-color)',
          background: 'rgba(6, 8, 20, 0.95)',
          backdropFilter: 'blur(16px)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-text-muted)', fontSize: '0.85rem', padding: '0.5rem 0' }}>
            <User size={14} />
            <span>{user.name || user.email}</span>
          </div>
          <NavLink
            to="/"
            onClick={() => setMobileMenuOpen(false)}
            className="glass-btn glass-btn-secondary"
            style={{ width: '100%', justifyContent: 'flex-start', padding: '0.6rem 0.85rem', fontSize: '0.85rem', textDecoration: 'none' }}
            end
          >
            <Layout size={14} />
            <span>Dashboard</span>
          </NavLink>
          <NavLink
            to="/knowledge-base"
            onClick={() => setMobileMenuOpen(false)}
            className="glass-btn glass-btn-secondary"
            style={{ width: '100%', justifyContent: 'flex-start', padding: '0.6rem 0.85rem', fontSize: '0.85rem', textDecoration: 'none' }}
          >
            <BookOpen size={14} />
            <span>Knowledge Base</span>
          </NavLink>

          <NavLink
            to="/settings"
            onClick={() => setMobileMenuOpen(false)}
            className="glass-btn glass-btn-secondary"
            style={{ width: '100%', justifyContent: 'flex-start', padding: '0.6rem 0.85rem', fontSize: '0.85rem', textDecoration: 'none' }}
          >
            <Settings size={14} />
            <span>Settings</span>
          </NavLink>
          <button
            onClick={handleLogout}
            className="glass-btn glass-btn-danger"
            style={{ width: '100%', justifyContent: 'flex-start', padding: '0.6rem 0.85rem', fontSize: '0.85rem' }}
          >
            <LogOut size={14} />
            <span>Log out</span>
          </button>
        </div>
      )}

      {/* Responsive CSS */}
      <style>{`
        @media (max-width: 768px) {
          .header-desktop-nav { display: none !important; }
          .header-mobile-toggle { display: flex !important; }
          .header-mobile-menu { display: flex !important; }
        }
      `}</style>
    </header>
  );
};

export default Header;
