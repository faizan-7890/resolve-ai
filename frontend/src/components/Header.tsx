import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { LogOut, Layout, Cpu, User, Settings, Menu, X } from 'lucide-react';

interface HeaderProps {
  onNavigate: (target: string) => void;
}

const Header: React.FC<HeaderProps> = ({ onNavigate }) => {
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
        <div 
          style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}
          onClick={() => onNavigate('dashboard')}
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
        </div>

        {/* Desktop Nav */}
        {user ? (
          <div className="header-desktop-nav" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <button 
              onClick={() => onNavigate('dashboard')}
              className="glass-btn glass-btn-secondary"
              style={{ padding: '0.45rem 0.85rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
            >
              <Layout size={14} />
              <span>Dashboard</span>
            </button>
            
            <button 
              onClick={() => onNavigate('settings')}
              className="glass-btn glass-btn-secondary"
              style={{ padding: '0.45rem 0.85rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
            >
              <Settings size={14} />
              <span>Settings</span>
            </button>

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
              onClick={logout}
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
            <span>AI Problem Workspace</span>
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
          <button 
            onClick={() => { onNavigate('dashboard'); setMobileMenuOpen(false); }}
            className="glass-btn glass-btn-secondary"
            style={{ width: '100%', justifyContent: 'flex-start', padding: '0.6rem 0.85rem', fontSize: '0.85rem' }}
          >
            <Layout size={14} />
            <span>Dashboard</span>
          </button>
          <button 
            onClick={() => { onNavigate('settings'); setMobileMenuOpen(false); }}
            className="glass-btn glass-btn-secondary"
            style={{ width: '100%', justifyContent: 'flex-start', padding: '0.6rem 0.85rem', fontSize: '0.85rem' }}
          >
            <Settings size={14} />
            <span>Settings</span>
          </button>
          <button 
            onClick={() => { logout(); setMobileMenuOpen(false); }}
            className="glass-btn glass-btn-danger"
            style={{ width: '100%', justifyContent: 'flex-start', padding: '0.6rem 0.85rem', fontSize: '0.85rem' }}
          >
            <LogOut size={14} />
            <span>Log out</span>
          </button>
        </div>
      )}

      {/* Responsive CSS for mobile menu */}
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
