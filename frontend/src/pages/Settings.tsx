import React, { useState, useEffect, useRef } from 'react';
import { useAuth, API_BASE } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import {
  Save, Key, User, Mail, Shield, Eye, EyeOff, Loader2, CheckCircle,
  Lock, Upload, FileText, X, CheckCheck, AlertTriangle, Database
} from 'lucide-react';

const Settings: React.FC = () => {
  const { user, token, changePassword } = useAuth();
  const { showToast } = useToast();

  // ── Profile state ────────────────────────────────────────────
  const [name, setName] = useState<string>(user?.name || '');
  const [hasNvidiaKey, setHasNvidiaKey] = useState<boolean>(false);
  const [hasOpenaiKey, setHasOpenaiKey] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);

  // ── Password change state ─────────────────────────────────────
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPw, setShowCurrentPw] = useState(false);
  const [showNewPw, setShowNewPw] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);

  // ── File upload state ─────────────────────────────────────────
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{
    document_id: number;
    document_title: string;
    chunks_count: number;
    file_size_kb: number;
  } | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Fetch settings ────────────────────────────────────────────
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const res = await fetch(`${API_BASE}/settings`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setName(data.name || '');
          setHasNvidiaKey(data.has_nvidia_key || false);
          setHasOpenaiKey(data.has_openai_key || false);
        }
      } catch (err) {
        console.error('Failed to fetch settings', err);
      }
    };
    fetchSettings();
  }, [token]);

  const getInitials = () => {
    const n = name || user?.email || 'U';
    return n.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2);
  };

  // ── Profile save ──────────────────────────────────────────────
  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/settings`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ name })
      });
      if (!res.ok) throw new Error('Failed to save settings.');
      const data = await res.json();
      setHasNvidiaKey(data.has_nvidia_key || false);
      setHasOpenaiKey(data.has_openai_key || false);
      showToast('Settings saved successfully!', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to save settings.', 'error');
    } finally {
      setSaving(false);
    }
  };

  // ── Password change ───────────────────────────────────────────
  const handleChangePassword = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      showToast('All password fields are required.', 'error');
      return;
    }
    if (newPassword !== confirmPassword) {
      showToast('New password and confirmation do not match.', 'error');
      return;
    }
    if (newPassword.length < 8) {
      showToast('New password must be at least 8 characters.', 'error');
      return;
    }
    setChangingPassword(true);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      showToast('Password changed successfully! Please log in again if prompted.', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to change password.', 'error');
    } finally {
      setChangingPassword(false);
    }
  };

  // ── File upload helpers ───────────────────────────────────────
  const ACCEPTED_TYPES = ['.pdf', '.docx', '.txt', '.md', '.csv', '.log'];
  const MAX_SIZE_MB = 10;

  const validateFile = (file: File): string | null => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ACCEPTED_TYPES.includes(ext)) {
      return `Unsupported file type "${ext}". Accepted: PDF, DOCX, TXT, MD, CSV`;
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return `File is too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Max: ${MAX_SIZE_MB} MB`;
    }
    return null;
  };

  const onFileSelect = (file: File) => {
    const err = validateFile(file);
    if (err) { showToast(err, 'error'); return; }
    setUploadFile(file);
    setUploadResult(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) onFileSelect(file);
  };

  const handleUpload = async () => {
    if (!uploadFile) return;
    setUploading(true);
    setUploadResult(null);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      const res = await fetch(`${API_BASE}/ingest/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Upload failed.');
      }
      const data = await res.json();
      setUploadResult(data);
      setUploadFile(null);
      showToast(`"${data.document_title}" ingested — ${data.chunks_count} chunks created`, 'success');
    } catch (err: any) {
      showToast(err.message || 'Upload failed.', 'error');
    } finally {
      setUploading(false);
    }
  };

  // ── Shared input style ────────────────────────────────────────
  const pwInputStyle: React.CSSProperties = {
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid var(--border-color)',
    borderRadius: '8px',
    padding: '0.6rem 2.5rem 0.6rem 0.85rem',
    color: 'var(--color-text-main)',
    fontSize: '0.9rem',
    width: '100%',
    outline: 'none'
  };

  const sectionHeader = (icon: React.ReactNode, label: string) => (
    <h2 style={{ fontSize: '1.1rem', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700 }}>
      {icon}
      {label}
    </h2>
  );

  return (
    <div className="app-container animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div>
        <h1 style={{ fontSize: '2.2rem', fontWeight: 800, marginBottom: '0.5rem' }}>
          Account Settings
        </h1>
        <p style={{ color: 'var(--color-text-muted)' }}>
          Manage your profile, security, and knowledge base configuration.
        </p>
      </div>

      <div className="settings-grid">
        {/* ── Left column: Profile card ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="glass-card-static">
            <div className="profile-card">
              <div className="profile-avatar">{getInitials()}</div>
              <div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>{name || 'User'}</h3>
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>{user?.email}</p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
                <span className="badge badge-indigo" style={{ textTransform: 'capitalize' }}>
                  <Shield size={10} style={{ marginRight: 4 }} />
                  {user?.role || 'user'}
                </span>
                {hasNvidiaKey && (
                  <span className="badge badge-teal">
                    <Key size={10} style={{ marginRight: 4 }} />
                    NVIDIA NIM
                  </span>
                )}
                {hasOpenaiKey && (
                  <span className="badge badge-indigo">
                    <Key size={10} style={{ marginRight: 4 }} />
                    OpenAI
                  </span>
                )}
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--color-text-dark)', marginTop: '0.5rem' }}>
                Member since {user?.created_at ? new Date(user.created_at as unknown as string).toLocaleDateString() : 'N/A'}
              </p>
            </div>
          </div>

          {/* ── API Status card ── */}
          <div className="glass-card-static">
            {sectionHeader(<Key size={16} color="var(--color-secondary)" />, 'API Configuration')}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                <span style={{ color: 'var(--color-text-muted)' }}>NVIDIA NIM API</span>
                {hasNvidiaKey ? (
                  <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <CheckCircle size={14} /> Active
                  </span>
                ) : (
                  <span style={{ color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <AlertTriangle size={14} /> Not Set
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.875rem' }}>
                <span style={{ color: 'var(--color-text-muted)' }}>OpenAI API</span>
                {hasOpenaiKey ? (
                  <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <CheckCircle size={14} /> Active
                  </span>
                ) : (
                  <span style={{ color: 'var(--color-text-dark)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <X size={14} /> Not Set
                  </span>
                )}
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--color-text-dark)', marginTop: '0.25rem' }}>
                API keys are managed via the backend <code style={{ background: 'rgba(255,255,255,0.08)', padding: '1px 5px', borderRadius: 4 }}>.env</code> file.
              </p>
            </div>
          </div>
        </div>

        {/* ── Right column: Forms ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

          {/* ── Profile form ── */}
          <div className="glass-card-static">
            {sectionHeader(<User size={16} color="var(--color-primary)" />, 'Profile')}
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
                  placeholder="Your display name"
                  className="glass-input"
                />
              </div>
              <button
                onClick={handleSave}
                disabled={saving}
                className="glass-btn glass-btn-primary"
                style={{ alignSelf: 'flex-start' }}
              >
                {saving ? <><Loader2 size={15} className="pulse-dots" /><span>Saving...</span></> : <><Save size={15} /><span>Save Profile</span></>}
              </button>
            </div>
          </div>

          {/* ── Password change form ── */}
          <div className="glass-card-static">
            {sectionHeader(<Lock size={16} color="var(--color-primary)" />, 'Change Password')}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>

              {/* Current password */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                <label style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', fontWeight: 500 }}>Current Password</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showCurrentPw ? 'text' : 'password'}
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="Enter current password"
                    style={pwInputStyle}
                  />
                  <button
                    onClick={() => setShowCurrentPw(!showCurrentPw)}
                    style={{ position: 'absolute', right: '0.6rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', padding: 0 }}
                  >
                    {showCurrentPw ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>

              {/* New password */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                <label style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', fontWeight: 500 }}>New Password</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showNewPw ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Min. 8 characters"
                    style={pwInputStyle}
                  />
                  <button
                    onClick={() => setShowNewPw(!showNewPw)}
                    style={{ position: 'absolute', right: '0.6rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', padding: 0 }}
                  >
                    {showNewPw ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
                {/* Strength indicator */}
                {newPassword && (
                  <div style={{ display: 'flex', gap: '0.25rem', marginTop: '0.25rem' }}>
                    {[...Array(4)].map((_, i) => {
                      const strength = [newPassword.length >= 8, /[A-Z]/.test(newPassword), /[0-9]/.test(newPassword), /[^A-Za-z0-9]/.test(newPassword)].filter(Boolean).length;
                      return (
                        <div key={i} style={{
                          height: '3px', flex: 1, borderRadius: '2px',
                          background: i < strength
                            ? strength <= 1 ? '#ef4444' : strength <= 2 ? '#f59e0b' : strength <= 3 ? '#6366f1' : '#10b981'
                            : 'rgba(255,255,255,0.1)'
                        }} />
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Confirm password */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                <label style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', fontWeight: 500 }}>Confirm New Password</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repeat new password"
                  style={{
                    ...pwInputStyle,
                    borderColor: confirmPassword && confirmPassword !== newPassword ? 'rgba(239,68,68,0.6)' : 'var(--border-color)'
                  }}
                />
                {confirmPassword && confirmPassword !== newPassword && (
                  <span style={{ fontSize: '0.75rem', color: '#f87171', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    <X size={12} /> Passwords do not match
                  </span>
                )}
                {confirmPassword && confirmPassword === newPassword && newPassword.length >= 8 && (
                  <span style={{ fontSize: '0.75rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    <CheckCheck size={12} /> Passwords match
                  </span>
                )}
              </div>

              <button
                onClick={handleChangePassword}
                disabled={changingPassword || !currentPassword || !newPassword || !confirmPassword}
                className="glass-btn glass-btn-primary"
                style={{ alignSelf: 'flex-start', marginTop: '0.25rem' }}
              >
                {changingPassword
                  ? <><Loader2 size={15} className="pulse-dots" /><span>Updating...</span></>
                  : <><Lock size={15} /><span>Update Password</span></>
                }
              </button>
            </div>
          </div>

          {/* ── File upload / Knowledge Base ingest ── */}
          <div className="glass-card-static">
            {sectionHeader(<Database size={16} color="var(--color-secondary)" />, 'Knowledge Base — Upload Document')}
            <p style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', marginBottom: '1rem' }}>
              Upload a PDF, Word document, or text file to the AI knowledge base. It will be automatically chunked and embedded for RAG retrieval.
            </p>

            {/* Drop zone */}
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleDrop}
              onClick={() => !uploadFile && fileInputRef.current?.click()}
              style={{
                border: `2px dashed ${isDragOver ? 'var(--color-primary)' : uploadFile ? '#10b981' : 'var(--border-color)'}`,
                borderRadius: '12px',
                padding: '2rem',
                textAlign: 'center',
                cursor: uploadFile ? 'default' : 'pointer',
                background: isDragOver ? 'rgba(99,102,241,0.07)' : uploadFile ? 'rgba(16,185,129,0.06)' : 'rgba(255,255,255,0.02)',
                transition: 'all 0.2s ease',
                marginBottom: '1rem'
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt,.md,.csv,.log"
                style={{ display: 'none' }}
                onChange={(e) => { const f = e.target.files?.[0]; if (f) onFileSelect(f); e.target.value = ''; }}
              />

              {uploadFile ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.75rem' }}>
                  <FileText size={22} color="#10b981" />
                  <div style={{ textAlign: 'left' }}>
                    <p style={{ fontWeight: 600, color: '#d1fae5', fontSize: '0.9rem' }}>{uploadFile.name}</p>
                    <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                      {(uploadFile.size / 1024).toFixed(0)} KB
                    </p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); setUploadFile(null); }}
                    style={{ background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '6px', color: '#f87171', cursor: 'pointer', padding: '0.25rem 0.5rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                  >
                    <X size={12} /> Remove
                  </button>
                </div>
              ) : (
                <div>
                  <Upload size={28} color="var(--color-text-dark)" style={{ marginBottom: '0.75rem' }} />
                  <p style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)', marginBottom: '0.25rem' }}>
                    <span style={{ color: 'var(--color-primary)', fontWeight: 600 }}>Click to upload</span> or drag &amp; drop
                  </p>
                  <p style={{ fontSize: '0.75rem', color: 'var(--color-text-dark)' }}>
                    PDF, DOCX, TXT, MD, CSV — up to {MAX_SIZE_MB} MB
                  </p>
                </div>
              )}
            </div>

            {/* Upload button */}
            <button
              onClick={handleUpload}
              disabled={!uploadFile || uploading}
              className="glass-btn glass-btn-primary"
              style={{ width: '100%' }}
            >
              {uploading
                ? <><Loader2 size={15} className="pulse-dots" /><span>Uploading &amp; Embedding...</span></>
                : <><Upload size={15} /><span>Upload to Knowledge Base</span></>
              }
            </button>

            {/* Success result */}
            {uploadResult && (
              <div style={{
                marginTop: '1rem',
                background: 'rgba(16,185,129,0.1)',
                border: '1px solid rgba(16,185,129,0.25)',
                borderRadius: '10px',
                padding: '1rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.4rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#10b981', fontWeight: 700, marginBottom: '0.25rem' }}>
                  <CheckCircle size={16} /> Document Ingested Successfully
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>
                  <span>📄 <strong style={{ color: '#d1fae5' }}>{uploadResult.document_title}</strong></span>
                  <span>🧩 {uploadResult.chunks_count} knowledge chunks created</span>
                  <span>📦 {uploadResult.file_size_kb} KB processed</span>
                  <span style={{ color: 'var(--color-text-dark)' }}>Document ID: #{uploadResult.document_id}</span>
                </div>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
};

export default Settings;
