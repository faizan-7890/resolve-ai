import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Cpu,
  Lock,
  Mail,
  ShieldCheck,
  Sparkles,
  User,
} from 'lucide-react';

const Auth: React.FC = () => {
  const { login, register } = useAuth();
  const [isLogin, setIsLogin] = useState<boolean>(true);
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [name, setName] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await register(email, name, password);
      }
    } catch (err: any) {
      setError(err.message || 'An authentication error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setIsLogin((current) => !current);
    setError(null);
  };

  return (
    <main className="auth-page animate-fade-in">
      <section className="auth-shell">
        <aside className="auth-side">
          <span className="eyebrow">
            <Sparkles size={14} />
            AI support command center
          </span>
          <h1>Resolve support tickets with traceable AI triage.</h1>
          <p>
            Route, diagnose, draft, and document every support case from one calm
            operations workspace.
          </p>

          <div className="auth-metrics" aria-label="ResolveAI capabilities">
            <div>
              <strong>RAG</strong>
              <span>policy-aware answers</span>
            </div>
            <div>
              <strong>SSE</strong>
              <span>live triage progress</span>
            </div>
            <div>
              <strong>JWT</strong>
              <span>secure sessions</span>
            </div>
          </div>

          <ul className="auth-feature-list">
            <li>
              <CheckCircle2 size={16} />
              AI clarifier, evaluator, writer, and auditor workflow
            </li>
            <li>
              <CheckCircle2 size={16} />
              Knowledge base ingestion with vector search memory
            </li>
            <li>
              <CheckCircle2 size={16} />
              Exportable ticket reports for support handoffs
            </li>
          </ul>
        </aside>

        <div className="auth-card glass-card-static">
          <div className="auth-card-header">
            <div className="brand-mark auth-brand-mark">
              <Cpu size={24} />
            </div>
            <div>
              <h2>{isLogin ? 'Welcome back' : 'Create your account'}</h2>
              <p>{isLogin ? 'Sign in to your support workspace.' : 'Start a ResolveAI workspace.'}</p>
            </div>
          </div>

          {error && (
            <div className="form-alert" role="alert">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="auth-form">
            {!isLogin && (
              <label className="form-field">
                <span>Name</span>
                <span className="input-shell">
                  <User size={18} />
                  <input
                    type="text"
                    required
                    placeholder="Your full name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="glass-input"
                  />
                </span>
              </label>
            )}

            <label className="form-field">
              <span>Email Address</span>
              <span className="input-shell">
                <Mail size={18} />
                <input
                  type="email"
                  required
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="glass-input"
                />
              </span>
            </label>

            <label className="form-field">
              <span>Password</span>
              <span className="input-shell">
                <Lock size={18} />
                <input
                  type="password"
                  required
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="glass-input"
                />
              </span>
            </label>

            <button type="submit" disabled={loading} className="glass-btn glass-btn-primary auth-submit">
              <span>{loading ? 'Authenticating...' : isLogin ? 'Sign in' : 'Create account'}</span>
              {!loading && <ArrowRight size={16} />}
            </button>
          </form>

          <div className="auth-switch">
            <ShieldCheck size={15} />
            <span>{isLogin ? "Don't have an account?" : 'Already have an account?'}</span>
            <button onClick={switchMode}>{isLogin ? 'Sign up' : 'Log in'}</button>
          </div>
        </div>
      </section>
    </main>
  );
};

export default Auth;
