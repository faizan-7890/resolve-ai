import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import Header from './components/Header';
import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';
import Workspace from './pages/Workspace';
import Settings from './pages/Settings';

type ViewState = 'dashboard' | 'workspace' | 'settings';

const InnerApp: React.FC = () => {
  const { token, loading } = useAuth();
  const [view, setView] = useState<ViewState>('dashboard');
  const [selectedProblemId, setSelectedProblemId] = useState<number | null>(null);

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#060814',
        color: '#fff',
        fontFamily: 'sans-serif',
        gap: '1rem'
      }}>
        <div style={{
          width: '40px',
          height: '40px',
          border: '4px solid rgba(99, 102, 241, 0.1)',
          borderTopColor: '#6366f1',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }} />
        <span>Authenticating secure node...</span>
        <style>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // Not logged in -> Show login/register
  if (!token) {
    return (
      <>
        <div className="space-bg" />
        <div className="glow-orb-1" />
        <div className="glow-orb-2" />
        <Header onNavigate={() => {}} />
        <Auth />
      </>
    );
  }

  const handleNavigate = (target: string) => {
    if (target === 'dashboard') {
      setView('dashboard');
      setSelectedProblemId(null);
    } else if (target === 'settings') {
      setView('settings');
      setSelectedProblemId(null);
    }
  };

  const handleSelectProblem = (id: number) => {
    setSelectedProblemId(id);
    setView('workspace');
  };

  const handleBackToDashboard = () => {
    setView('dashboard');
    setSelectedProblemId(null);
  };

  // Logged in -> Show dashboard, workspace, or settings
  return (
    <>
      <div className="space-bg" />
      <div className="glow-orb-1" />
      <div className="glow-orb-2" />
      <Header onNavigate={handleNavigate} />
      {view === 'settings' ? (
        <Settings />
      ) : view === 'workspace' && selectedProblemId !== null ? (
        <Workspace 
          problemId={selectedProblemId} 
          onBack={handleBackToDashboard} 
        />
      ) : (
        <Dashboard onSelectProblem={handleSelectProblem} />
      )}
    </>
  );
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <ToastProvider>
        <InnerApp />
      </ToastProvider>
    </AuthProvider>
  );
};

export default App;
