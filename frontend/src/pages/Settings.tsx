import React, { useState, useEffect } from 'react';
import { useAuth, API_BASE } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { 
  Save, Key, User, Mail, Shield, Eye, EyeOff, Loader2, CheckCircle
} from 'lucide-react';

const Settings: React.FC = () => {
  const { user, token } = useAuth();
  const { showToast } = useToast();

  const [name, setName] = useState<string>(user?.name || '');
  const [openaiKey, setOpenaiKey] = useState<string>('');
  const [showKey, setShowKey] = useState<boolean>(false);
  const [hasStoredKey, setHasStoredKey] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);

  useEffect(() => {
    // Fetch current settings
    const fetchSettings = async () => {
      try {
        const res = await fetch(`${API_BASE}/settings`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setName(data.name || '');
          setHasStoredKey(data.has_openai_key || false);
        }
      } catch (err) {
        console.error("Failed to fetch settings", err);
      }
    };
    fetchSettings();
  }, [token]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const body: Record<string, string> = { name };
      if (openaiKey.trim()) {
        body.openai_api_key = openaiKey.trim();
      }

      const res = await fetch(`${API_BASE}/settings`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(body)
      });

      if (!res.ok) throw new Error("Failed to save settings.");

      const data = await res.json();
      setHasStoredKey(data.has_openai_key || false);
      setOpenaiKey('');
      showToast('Settings saved successfully!', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to save settings.', 'error');
    } finally {
      setSaving(false);
    }
  };

  const getInitials = () => {
    const n = name || user?.email || 'U';
    return n.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
  };

  return (
    <div className="app-container animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div>
        <h1 style={{ fontSize: '2.2rem', fontWeight: 800, marginBottom: '0.5rem' }}>
          Account Settings
        </h1>
        <p style={{ color: 'var(--color-text-muted)' }}>
          Manage your profile and configure API keys for live AI agents.
        </p>
      </div>

      <div className="settings-grid">
        {/* Profile Card */}
        <div className="glass-card-static">
          <div className="profile-card">
            <div className="profile-avatar">
              {getInitials()}
            </div>
            <div>
              <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>{name || 'User'}</h3>
              <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>{user?.email}</p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
              <span className="badge badge-indigo" style={{ textTransform: 'capitalize' }}>
                <Shield size={10} style={{ marginRight: 4 }} />
                {user?.role || 'user'}
              </span>
              {hasStoredKey && (
                <span className="badge badge-teal">
                  <Key size={10} style={{ marginRight: 4 }} />
                  API Connected
                </span>
              )}
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--color-text-dark)', marginTop: '0.5rem' }}>
              Member since {user?.created_at ? new Date(user.created_at as unknown as string).toLocaleDateString() : 'N/A'}
            </p>
          </div>
        </div>

        {/* Settings Form */}
        <div className="glass-card-static">
          <h2 style={{ fontSize: '1.3rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <User size={18} color="var(--color-primary)" />
            Profile & Configuration
          </h2>
          
          <div className="settings-form">
            <div className="settings-field">
              <label>
                <Mail size={12} style={{ marginRight: 4, verticalAlign: 'middle' }} />
                Email Address
              </label>
              <input
                type="email"
                value={user?.email || ''}
                disabled
                className="glass-input"
                style={{ opacity: 0.6, cursor: 'not-allowed' }}
              />
            </div>

            <div className="settings-field">
              <label>
                <User size={12} style={{ marginRight: 4, verticalAlign: 'middle' }} />
                Display Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter your display name"
                className="glass-input"
              />
            </div>

            <div className="settings-field">
              <label>
                <Key size={12} style={{ marginRight: 4, verticalAlign: 'middle' }} />
                OpenAI API Key
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showKey ? 'text' : 'password'}
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  placeholder={hasStoredKey ? '••••••••••••••••••••••  (key stored)' : 'sk-...'}
                  className="glass-input"
                  style={{ paddingRight: '3rem' }}
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  style={{
                    position: 'absolute',
                    right: '0.75rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    color: 'var(--color-text-dark)',
                    cursor: 'pointer',
                    padding: '0.25rem'
                  }}
                >
                  {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              <p className="api-key-hint">
                {hasStoredKey ? (
                  <span style={{ color: 'var(--color-success)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    <CheckCircle size={12} />
                    API key is configured. Leave blank to keep current key, or enter a new one to replace it.
                  </span>
                ) : (
                  'Paste your OpenAI API key to enable real AI-powered agents. Without a key, mock responses are used.'
                )}
              </p>
            </div>

            <button
              onClick={handleSave}
              disabled={saving}
              className="glass-btn glass-btn-primary"
              style={{ marginTop: '0.5rem', alignSelf: 'flex-start' }}
            >
              {saving ? (
                <>
                  <Loader2 size={16} className="pulse-dots" />
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Save size={16} />
                  <span>Save Changes</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
