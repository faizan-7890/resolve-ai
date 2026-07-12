import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import Header from './components/Header';
import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';
import Workspace from './pages/Workspace';
import Settings from './pages/Settings';

// Route guard — redirects to /login if not authenticated
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token, loading } = useAuth();

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
          @keyframes spin { to { transform: rotate(360deg); } }
        `}</style>
      </div>
    );
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

// Layout wrapper for authenticated pages (includes background + header)
const AuthenticatedLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <>
    <div className="space-bg" />
    <div className="glow-orb-1" />
    <div className="glow-orb-2" />
    <Header />
    {children}
  </>
);

const AppRoutes: React.FC = () => {
  const { token } = useAuth();

  return (
    <Routes>
      {/* Public: login/register */}
      <Route
        path="/login"
        element={
          token ? (
            <Navigate to="/" replace />
          ) : (
            <>
              <div className="space-bg" />
              <div className="glow-orb-1" />
              <div className="glow-orb-2" />
              <Header />
              <Auth />
            </>
          )
        }
      />

      {/* Protected: Dashboard */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <Dashboard />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />

      {/* Protected: Ticket Workspace */}
      <Route
        path="/tickets/:id"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <Workspace />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />

      {/* Protected: Settings */}
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <AuthenticatedLayout>
              <Settings />
            </AuthenticatedLayout>
          </ProtectedRoute>
        }
      />

      {/* Catch-all: redirect to home */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <AppRoutes />
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
