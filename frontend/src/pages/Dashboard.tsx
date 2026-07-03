import React, { useState, useEffect } from 'react';
import { useAuth, API_BASE } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { 
  Plus, Briefcase, GraduationCap, Building2, User as UserIcon, HelpCircle, 
  AlertTriangle, Folder, PlayCircle, Loader2, ArrowUpRight, Trash2, CheckCircle2,
  BarChart3, PieChart, Target, TrendingUp
} from 'lucide-react';

interface Problem {
  id: number;
  title: string;
  description: string;
  category: string;
  urgency: string;
  status: string;
  created_at: string;
}

interface AnalyticsData {
  status_counts: Record<string, number>;
  category_counts: Record<string, number>;
  task_completion: { total: number; completed: number; rate: number };
  recent_activity: Array<{ title: string; status: string; created_at: string }>;
}

interface DashboardProps {
  onSelectProblem: (id: number) => void;
}

const STATUS_COLORS: Record<string, string> = {
  'Intake': '#6366f1',
  'Clarifying': '#a855f7',
  'Diagnosing': '#f59e0b',
  'Planning': '#3b82f6',
  'Execution': '#14b8a6',
  'Resolved': '#10b981',
};

const CATEGORY_COLORS: Record<string, string> = {
  'General': '#6366f1',
  'Career': '#3b82f6',
  'Academic': '#a855f7',
  'Business': '#14b8a6',
  'Personal': '#f59e0b',
};

const Dashboard: React.FC<DashboardProps> = ({ onSelectProblem }) => {
  const { token } = useAuth();
  const { showToast } = useToast();
  const [problems, setProblems] = useState<Problem[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  
  // Intake Form States
  const [title, setTitle] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [category, setCategory] = useState<string>('General');
  const [urgency, setUrgency] = useState<string>('Medium');
  
  const [error, setError] = useState<string | null>(null);

  const fetchProblems = async () => {
    try {
      const res = await fetch(`${API_BASE}/problems`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setProblems(data);
      }
    } catch (err) {
      console.error("Error fetching problems", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const res = await fetch(`${API_BASE}/analytics`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setAnalytics(data);
      }
    } catch (err) {
      console.error("Error fetching analytics", err);
    }
  };

  useEffect(() => {
    fetchProblems();
    fetchAnalytics();
  }, [token]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const res = await fetch(`${API_BASE}/problems`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ title, description, category, urgency })
      });

      if (!res.ok) {
        throw new Error("Failed to create problem workspace.");
      }

      const newProblem = await res.json();
      setTitle('');
      setDescription('');
      setCategory('General');
      setUrgency('Medium');
      showToast('Problem workspace created successfully!', 'success');
      
      // Auto open the newly created workspace
      onSelectProblem(newProblem.id);
    } catch (err: any) {
      setError(err.message || "Something went wrong.");
      showToast(err.message || 'Failed to create workspace.', 'error');
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation(); // Avoid triggering open workspace
    if (!window.confirm("Are you sure you want to delete this problem workspace?")) return;

    try {
      const res = await fetch(`${API_BASE}/problems/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        setProblems(problems.filter(p => p.id !== id));
        showToast('Workspace deleted.', 'info');
        fetchAnalytics();
      }
    } catch (err) {
      console.error("Failed to delete workspace", err);
      showToast('Failed to delete workspace.', 'error');
    }
  };

  // Helper icons for categories
  const getCategoryIcon = (cat: string) => {
    switch (cat) {
      case 'Career': return <Briefcase size={16} />;
      case 'Academic': return <GraduationCap size={16} />;
      case 'Business': return <Building2 size={16} />;
      case 'Personal': return <UserIcon size={16} />;
      default: return <HelpCircle size={16} />;
    }
  };

  const getUrgencyBadge = (urg: string) => {
    switch (urg) {
      case 'High': return <span className="badge badge-rose">{urg}</span>;
      case 'Medium': return <span className="badge badge-amber">{urg}</span>;
      default: return <span className="badge badge-teal">{urg}</span>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'Resolved': return <span className="badge badge-teal" style={{ background: 'rgba(16, 185, 129, 0.2)' }}><CheckCircle2 size={12} style={{ marginRight: 4 }} /> {status}</span>;
      case 'Execution': return <span className="badge badge-violet">{status}</span>;
      case 'Planning': return <span className="badge badge-indigo">{status}</span>;
      default: return <span className="badge badge-teal">{status}</span>;
    }
  };

  // Calculate aggregates
  const totalProblems = problems.length;
  const activeProblems = problems.filter(p => p.status !== 'Resolved').length;
  const resolvedProblems = problems.filter(p => p.status === 'Resolved').length;

  // SVG Donut Chart helper
  const renderDonutChart = (data: Record<string, number>) => {
    const total = Object.values(data).reduce((s, v) => s + v, 0);
    if (total === 0) return <p style={{ color: 'var(--color-text-dark)', fontSize: '0.85rem' }}>No data yet</p>;
    
    const size = 160;
    const strokeWidth = 22;
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    let currentOffset = 0;

    return (
      <div className="chart-container">
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {Object.entries(data).map(([key, value]) => {
            if (value === 0) return null;
            const pct = value / total;
            const dashLength = circumference * pct;
            const dashOffset = circumference * currentOffset;
            currentOffset += pct;
            const color = STATUS_COLORS[key] || '#6366f1';
            return (
              <circle
                key={key}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={color}
                strokeWidth={strokeWidth}
                strokeDasharray={`${dashLength} ${circumference - dashLength}`}
                strokeDashoffset={-dashOffset}
                strokeLinecap="round"
                style={{ 
                  transform: 'rotate(-90deg)', 
                  transformOrigin: 'center',
                  transition: 'stroke-dasharray 1s ease'
                }}
              />
            );
          })}
          <text x="50%" y="50%" textAnchor="middle" dy="0.35em" fill="#fff" fontSize="1.8rem" fontWeight="700" fontFamily="var(--font-title)">
            {total}
          </text>
        </svg>
        <div className="chart-legend">
          {Object.entries(data).map(([key, value]) => (
            value > 0 && (
              <div key={key} className="chart-legend-item">
                <div className="chart-legend-dot" style={{ background: STATUS_COLORS[key] || '#6366f1' }} />
                <span>{key} ({value})</span>
              </div>
            )
          ))}
        </div>
      </div>
    );
  };

  // Progress ring
  const renderProgressRing = (rate: number, completed: number, total: number) => {
    const size = 120;
    const strokeWidth = 10;
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const fillLength = circumference * (rate / 100);
    
    return (
      <div className="chart-container">
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none" stroke="rgba(255,255,255,0.05)"
            strokeWidth={strokeWidth}
          />
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none" stroke="var(--color-secondary)"
            strokeWidth={strokeWidth}
            strokeDasharray={`${fillLength} ${circumference - fillLength}`}
            strokeDashoffset={0}
            strokeLinecap="round"
            style={{ transform: 'rotate(-90deg)', transformOrigin: 'center', transition: 'stroke-dasharray 1s ease' }}
          />
          <text x="50%" y="46%" textAnchor="middle" fill="#fff" fontSize="1.4rem" fontWeight="700" fontFamily="var(--font-title)">
            {Math.round(rate)}%
          </text>
          <text x="50%" y="62%" textAnchor="middle" fill="var(--color-text-dark)" fontSize="0.6rem" fontWeight="500">
            {completed}/{total} tasks
          </text>
        </svg>
      </div>
    );
  };

  return (
    <div className="app-container animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      
      {/* Welcome Banner */}
      <div>
        <h1 style={{ fontSize: '2.2rem', fontWeight: 800, marginBottom: '0.5rem' }}>
          Problem Diagnostics Dashboard
        </h1>
        <p style={{ color: 'var(--color-text-muted)' }}>
          Create a new structured workspace or resume planning for your active cases below.
        </p>
      </div>

      {/* Aggregate Stats Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '1.25rem'
      }}>
        <div className="glass-card-static" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <span style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', fontWeight: 600 }}>TOTAL PROBLEMS</span>
            <h3 style={{ fontSize: '2rem', fontWeight: 800, marginTop: '0.25rem' }}>{totalProblems}</h3>
          </div>
          <Folder size={32} color="var(--color-primary)" style={{ opacity: 0.8 }} />
        </div>
        <div className="glass-card-static" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <span style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', fontWeight: 600 }}>ACTIVE DIAGNOSTICS</span>
            <h3 style={{ fontSize: '2rem', fontWeight: 800, marginTop: '0.25rem' }}>{activeProblems}</h3>
          </div>
          <PlayCircle size={32} color="var(--color-secondary)" style={{ opacity: 0.8 }} />
        </div>
        <div className="glass-card-static" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <span style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', fontWeight: 600 }}>RESOLVED SYSTEMS</span>
            <h3 style={{ fontSize: '2rem', fontWeight: 800, marginTop: '0.25rem' }}>{resolvedProblems}</h3>
          </div>
          <CheckCircle2 size={32} color="var(--color-success)" style={{ opacity: 0.8 }} />
        </div>
      </div>

      {/* Analytics Section */}
      {analytics && (totalProblems > 0) && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h2 style={{ fontSize: '1.4rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <BarChart3 size={20} color="var(--color-accent)" />
            <span>Analytics Overview</span>
          </h2>
          <div className="analytics-grid">
            {/* Status Distribution Donut */}
            <div className="glass-card-static" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <PieChart size={16} color="var(--color-primary)" />
                <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>Status Distribution</span>
              </div>
              {renderDonutChart(analytics.status_counts)}
            </div>

            {/* Category Breakdown Bars */}
            <div className="glass-card-static" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <TrendingUp size={16} color="var(--color-secondary)" />
                <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>Category Breakdown</span>
              </div>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                {Object.entries(analytics.category_counts).map(([cat, count]) => {
                  const maxCount = Math.max(...Object.values(analytics.category_counts), 1);
                  const pct = (count / maxCount) * 100;
                  return (
                    <div key={cat} className="bar-chart-row">
                      <span className="bar-chart-label">{cat}</span>
                      <div className="bar-chart-track">
                        <div 
                          className="bar-chart-fill" 
                          style={{ 
                            width: `${Math.max(pct, 8)}%`, 
                            background: `linear-gradient(90deg, ${CATEGORY_COLORS[cat] || '#6366f1'}, ${CATEGORY_COLORS[cat] || '#6366f1'}88)` 
                          }}
                        >
                          {count}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Task Completion Ring */}
            <div className="glass-card-static" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Target size={16} color="var(--color-success)" />
                <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>Task Completion</span>
              </div>
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {renderProgressRing(
                  analytics.task_completion.rate,
                  analytics.task_completion.completed,
                  analytics.task_completion.total
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Split view: Create Problem vs Problem List */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1.2fr 2fr',
        gap: '2rem',
        alignItems: 'start'
      }}>
        
        {/* Left Side: Create Workspace Form */}
        <div className="glass-card-static" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <h2 style={{ fontSize: '1.4rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Plus size={20} color="var(--color-secondary)" />
            <span>New Workspace</span>
          </h2>
          
          {error && (
            <div style={{ color: 'red', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <AlertTriangle size={14} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
              <label style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', fontWeight: 500 }}>Problem Title</label>
              <input
                type="text"
                required
                placeholder="e.g., Weak Interview Shortlisting"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="glass-input"
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
              <label style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', fontWeight: 500 }}>Description (Describe in plain English)</label>
              <textarea
                required
                rows={5}
                placeholder="Detail what is happening, what symptoms you see, and any constraints you are facing..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="glass-input"
                style={{ resize: 'none' }}
              />
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '0.75rem'
            }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
                <label style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', fontWeight: 500 }}>Category</label>
                <select 
                  value={category} 
                  onChange={(e) => setCategory(e.target.value)} 
                  className="glass-input"
                  style={{ background: '#060814' }}
                >
                  <option value="General">General</option>
                  <option value="Career">Career</option>
                  <option value="Academic">Academic</option>
                  <option value="Business">Business</option>
                  <option value="Personal">Personal</option>
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
                <label style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', fontWeight: 500 }}>Urgency</label>
                <select 
                  value={urgency} 
                  onChange={(e) => setUrgency(e.target.value)} 
                  className="glass-input"
                  style={{ background: '#060814' }}
                >
                  <option value="Low">Low</option>
                  <option value="Medium">Medium</option>
                  <option value="High">High</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="glass-btn glass-btn-primary"
              style={{ marginTop: '0.5rem', width: '100%' }}
            >
              {submitting ? (
                <>
                  <Loader2 size={16} className="pulse-dots" />
                  <span>Creating Workspace...</span>
                </>
              ) : (
                <>
                  <Plus size={16} />
                  <span>Launch Diagnostics</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Side: Workspace List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h2 style={{ fontSize: '1.4rem' }}>Active Workspaces</h2>
            <span style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>Ordered by date</span>
          </div>

          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
              <Loader2 size={32} className="pulse-dots" style={{ color: 'var(--color-primary)' }} />
            </div>
          ) : problems.length === 0 ? (
            <div className="glass-card" style={{ textAlign: 'center', padding: '3rem 2rem', color: 'var(--color-text-muted)' }}>
              <HelpCircle size={40} style={{ marginBottom: '1rem', opacity: 0.5 }} />
              <p style={{ fontWeight: 500 }}>No workspaces created yet.</p>
              <p style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>Submit the form on the left to activate your first diagnostics project.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {problems.map((prob) => (
                <div 
                  key={prob.id} 
                  className="glass-card"
                  onClick={() => onSelectProblem(prob.id)}
                  style={{
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.75rem',
                    position: 'relative'
                  }}
                >
                  {/* Top line header */}
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem' }}>
                    <h3 style={{ fontSize: '1.15rem', color: '#fff', fontWeight: 600 }}>{prob.title}</h3>
                    <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
                      {getUrgencyBadge(prob.urgency)}
                      {getStatusBadge(prob.status)}
                    </div>
                  </div>

                  {/* Body text snippet */}
                  <p style={{
                    fontSize: '0.875rem',
                    color: 'var(--color-text-muted)',
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                    lineHeight: '1.4'
                  }}>
                    {prob.description}
                  </p>

                  {/* Footer metadata */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginTop: '0.5rem',
                    paddingTop: '0.75rem',
                    borderTop: '1px solid rgba(255,255,255,0.04)',
                    fontSize: '0.8rem',
                    color: 'var(--color-text-dark)'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      {getCategoryIcon(prob.category)}
                      <span>{prob.category}</span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <span>Started {new Date(prob.created_at).toLocaleDateString()}</span>
                      
                      <button 
                        onClick={(e) => handleDelete(prob.id, e)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#f87171',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.25rem',
                          padding: '0.25rem',
                          borderRadius: '4px'
                        }}
                        className="glass-btn-danger"
                      >
                        <Trash2 size={13} />
                      </button>
                      
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.15rem', color: 'var(--color-primary)', fontWeight: 600 }}>
                        <span>Analyze</span>
                        <ArrowUpRight size={14} />
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Responsive override for dashboard grid */}
      <style>{`
        @media (max-width: 768px) {
          div[style*="gridTemplateColumns: '1.2fr 2fr'"],
          div[style*="grid-template-columns"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
};

export default Dashboard;
