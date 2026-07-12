import React, { createContext, useState, useEffect, useContext, useCallback, useRef } from 'react';

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

interface User {
  id: number;
  email: string;
  name: string;
  role: string;
  created_at?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, name: string, password: string) => Promise<void>;
  logout: () => void;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Decode JWT expiry without a library
function getTokenExpiry(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('resolve_ai_token'));
  const [loading, setLoading] = useState<boolean>(true);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Schedule auto-refresh 5 minutes before expiry
  const scheduleRefresh = useCallback((tkn: string) => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    const expiry = getTokenExpiry(tkn);
    if (!expiry) return;

    const now = Date.now();
    const msUntilRefresh = expiry - now - 5 * 60 * 1000; // 5 min before expiry

    if (msUntilRefresh <= 0) return; // Already near expiry, don't schedule

    refreshTimerRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${tkn}` }
        });
        if (res.ok) {
          const data = await res.json();
          localStorage.setItem('resolve_ai_token', data.access_token);
          setToken(data.access_token);
          scheduleRefresh(data.access_token);
        }
      } catch (err) {
        console.warn('Token auto-refresh failed:', err);
      }
    }, msUntilRefresh);
  }, []);

  useEffect(() => {
    const fetchUser = async () => {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const res = await fetch(`${API_BASE}/auth/me`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setUser(data);
          scheduleRefresh(token);
        } else {
          logout();
        }
      } catch (err) {
        console.error("Error fetching user session", err);
      } finally {
        setLoading(false);
      }
    };
    fetchUser();

    return () => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    };
  }, [token]);

  const login = async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || "Invalid login credentials.");
    }

    const data = await res.json();
    localStorage.setItem('resolve_ai_token', data.access_token);
    setToken(data.access_token);
  };

  const register = async (email: string, name: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, name, password })
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || "Registration failed.");
    }

    await login(email, password);
  };

  const logout = () => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    localStorage.removeItem('resolve_ai_token');
    setToken(null);
    setUser(null);
  };

  const changePassword = async (currentPassword: string, newPassword: string) => {
    const res = await fetch(`${API_BASE}/auth/change-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || "Failed to change password.");
    }
  };

  const refreshToken = async () => {
    if (!token) return;
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      const data = await res.json();
      localStorage.setItem('resolve_ai_token', data.access_token);
      setToken(data.access_token);
      scheduleRefresh(data.access_token);
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout, changePassword, refreshToken }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
