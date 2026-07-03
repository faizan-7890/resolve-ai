import React, { createContext, useContext, useState, useCallback } from 'react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: number;
  message: string;
  type: ToastType;
  exiting: boolean;
}

interface ToastContextType {
  showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

let toastIdCounter = 0;

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((message: string, type: ToastType = 'info') => {
    const id = ++toastIdCounter;
    setToasts(prev => [...prev, { id, message, type, exiting: false }]);

    // Start exit animation after 3.5s
    setTimeout(() => {
      setToasts(prev => prev.map(t => t.id === id ? { ...t, exiting: true } : t));
    }, 3500);

    // Remove from DOM after exit animation completes
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  }, []);

  const getIcon = (type: ToastType) => {
    switch (type) {
      case 'success': return '✓';
      case 'error': return '✕';
      case 'warning': return '⚠';
      case 'info': return 'ℹ';
    }
  };

  const getTypeClass = (type: ToastType) => {
    switch (type) {
      case 'success': return 'toast-success';
      case 'error': return 'toast-error';
      case 'warning': return 'toast-warning';
      case 'info': return 'toast-info';
    }
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {/* Toast Container */}
      <div style={{
        position: 'fixed',
        top: '1.25rem',
        right: '1.25rem',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
        pointerEvents: 'none',
        maxWidth: '420px',
        width: '100%',
      }}>
        {toasts.map(toast => (
          <div
            key={toast.id}
            className={`toast-notification ${getTypeClass(toast.type)} ${toast.exiting ? 'toast-exit' : 'toast-enter'}`}
            style={{ pointerEvents: 'auto' }}
          >
            <div className="toast-icon-wrapper">
              <span className="toast-icon">{getIcon(toast.type)}</span>
            </div>
            <p className="toast-message">{toast.message}</p>
            <button
              className="toast-close"
              onClick={() => {
                setToasts(prev => prev.map(t => t.id === toast.id ? { ...t, exiting: true } : t));
                setTimeout(() => {
                  setToasts(prev => prev.filter(t => t.id !== toast.id));
                }, 400);
              }}
            >
              ✕
            </button>
            <div className="toast-progress-bar" />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
