import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth, API_BASE } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { 
  ArrowLeft, Cpu, HelpCircle, AlertTriangle, Loader2, Play, CheckSquare, 
  ListTodo, Layers, Activity, Award, CheckCircle, Lightbulb, BookOpen, Compass,
  ChevronDown, ChevronUp, Download, Clock
} from 'lucide-react';

interface Clarification {
  id: number;
  question: string;
  answer: string | null;
}

interface Diagnosis {
  id: number;
  root_causes: string;     // JSON string array
  swot_analysis: string;   // JSON string object
  first_principles: string; // JSON string array
}

interface Solution {
  id: number;
  title: string;
  strategy_details: string;
  score: number;
  impact: number;
  confidence: number;
  risk: number;
  constraints: string | null;
  selected: boolean;
}

interface Task {
  id: number;
  title: string;
  status: string;
  priority: string;
  timeline: string | null;
}

interface Problem {
  id: number;
  title: string;
  description: string;
  category: string;
  urgency: string;
  status: string;
  created_at: string;
  clarifications: Clarification[];
  diagnoses: Diagnosis[];
  solutions: Solution[];
  tasks: Task[];
}

interface SimilarCase {
  id: number;
  problem_summary: string;
  solution_summary: string;
  similarity: number;
}

interface ActivityEntry {
  id: number;
  action: string;
  detail: string | null;
  created_at: string;
}

interface WorkspaceProps {}

const Workspace: React.FC<WorkspaceProps> = () => {
  const { id } = useParams<{ id: string }>();
  const problemId = parseInt(id || '0', 10);
  const navigate = useNavigate();
  const { token } = useAuth();
  const { showToast } = useToast();
  const [problem, setProblem] = useState<Problem | null>(null);
  const [similarCases, setSimilarCases] = useState<SimilarCase[]>([]);
  const [activityLog, setActivityLog] = useState<ActivityEntry[]>([]);
  const [activityOpen, setActivityOpen] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Operation Loaders
  const [aiLoading, setAiLoading] = useState<boolean>(false);
  const [agentSteps, setAgentSteps] = useState<Array<{step: string; status: string; detail?: string; decision?: string; passed?: boolean}>>([]);
  const [answers, setAnswers] = useState<Record<number, string>>({});

  const fetchWorkspace = async () => {
    try {
      const res = await fetch(`${API_BASE}/tickets/${problemId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Could not load problem workspace.");
      const data = await res.json();
      setProblem(data);
      
      // Initialize clarification answers
      const initialAnswers: Record<number, string> = {};
      data.clarifications.forEach((c: Clarification) => {
        initialAnswers[c.id] = c.answer || '';
      });
      setAnswers(initialAnswers);

      // If in execution or resolved state, load similar cases (RAG memory)
      if (data.status === 'Execution' || data.status === 'Resolved' || data.status === 'Open') {
        fetchSimilarCases();
      }
      // Always fetch activity log
      fetchActivityLog();
    } catch (err: any) {
      setError(err.message || "Failed to load workspace.");
    } finally {
      setLoading(false);
    }
  };

  const fetchSimilarCases = async () => {
    try {
      const res = await fetch(`${API_BASE}/tickets/${problemId}/similar`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSimilarCases(data);
      }
    } catch (err) {
      console.error("Failed to load similar memories", err);
    }
  };

  const fetchActivityLog = async () => {
    try {
      const res = await fetch(`${API_BASE}/tickets/${problemId}/activity`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setActivityLog(data);
      }
    } catch (err) {
      console.error("Failed to load activity log", err);
    }
  };

  const handleExportReport = async () => {
    try {
      const res = await fetch(`${API_BASE}/tickets/${problemId}/export`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Export failed.");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `resolveai-report-${problemId}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      showToast('Report exported successfully!', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to export report.', 'error');
    }
  };

  useEffect(() => {
    fetchWorkspace();
  }, [problemId, token]);

  const handleGenerateClarifications = async () => {
    setAiLoading(true);
    try {
      const res = await fetch(`${API_BASE}/tickets/${problemId}/clarify/generate`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Clarification generation failed.");
      await fetchWorkspace();
      showToast('Clarifying questions generated successfully.', 'success');
    } catch (err: any) {
      showToast(err.message || 'AI failed to generate clarifications.', 'error');
    } finally {
      setAiLoading(false);
    }
  };

  const handleSubmitAnswers = async () => {
    setAiLoading(true);
    try {
      const answerList = Object.entries(answers).map(([id, text]) => ({
        clarification_id: parseInt(id),
        answer: text
      }));
      
      const res = await fetch(`${API_BASE}/tickets/${problemId}/clarify/answer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ answers: answerList })
      });
      
      if (!res.ok) throw new Error("Submitting answers failed.");
      await fetchWorkspace();
      showToast('Answers submitted — ready for diagnosis.', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to submit answers.', 'error');
    } finally {
      setAiLoading(false);
    }
  };

  const handleRunDiagnosis = () => {
    setAiLoading(true);
    setAgentSteps([]);

    const url = `${API_BASE}/tickets/${problemId}/diagnose/stream`;
    const es = new EventSource(url + `?token=${encodeURIComponent(token || '')}`);

    // Note: EventSource doesn't support custom headers, so we use the streaming
    // GET endpoint. The token is sent as a query param for SSE auth.
    // A more secure alternative is a cookie-based session.
    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setAgentSteps(prev => {
          // Update or append this step
          const existing = prev.findIndex(s => s.step === data.step && s.status === 'running');
          if (existing >= 0 && data.status === 'done') {
            const updated = [...prev];
            updated[existing] = data;
            return updated;
          }
          return [...prev, data];
        });

        if (data.step === 'complete') {
          es.close();
          setAiLoading(false);
          fetchWorkspace();
          showToast(`Triage complete — ${data.decision}`, 'success');
        }
      } catch (e) {
        console.error('SSE parse error', e);
      }
    };

    es.onerror = () => {
      es.close();
      setAiLoading(false);
      // Fallback to synchronous diagnose if SSE fails
      fetch(`${API_BASE}/tickets/${problemId}/diagnose`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })
        .then(res => { if (!res.ok) throw new Error(); return res; })
        .then(() => { fetchWorkspace(); showToast('Diagnosis complete.', 'success'); })
        .catch(() => showToast('Diagnosis failed. Please retry.', 'error'));
    };
  };

  const handleGenerateSolutions = async () => {
    setAiLoading(true);
    try {
      const res = await fetch(`${API_BASE}/tickets/${problemId}/solutions`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Solutions strategist run failed.");
      await fetchWorkspace();
      showToast('Solutions generated and scored by strategist agents.', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to generate solutions.', 'error');
    } finally {
      setAiLoading(false);
    }
  };

  const handleSelectSolution = async (solId: number) => {
    try {
      const res = await fetch(`${API_BASE}/tickets/${problemId}/solutions/${solId}/select`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Selecting strategy failed.");
      await fetchWorkspace();
      showToast('Strategy selected as primary approach.', 'info');
    } catch (err: any) {
      showToast(err.message || 'Failed to select strategy.', 'error');
    }
  };

  const handleGeneratePlan = async () => {
    setAiLoading(true);
    try {
      const res = await fetch(`${API_BASE}/tickets/${problemId}/plan`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Roadmap generation failed.");
      await fetchWorkspace();
      showToast('Execution roadmap generated with milestones.', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to generate execution plan.', 'error');
    } finally {
      setAiLoading(false);
    }
  };

  const handleToggleTask = async (taskId: number, currentStatus: string) => {
    const nextStatus = currentStatus === 'Done' ? 'Pending' : 'Done';
    try {
      const res = await fetch(`${API_BASE}/tickets/${problemId}/tasks/${taskId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ status: nextStatus })
      });
      if (res.ok) {
        // Optimistic toggle locally
        if (problem) {
          const updatedTasks = problem.tasks.map(t => t.id === taskId ? { ...t, status: nextStatus } : t);
          setProblem({ ...problem, tasks: updatedTasks });
        }
      }
    } catch (err) {
      console.error("Failed to update task status", err);
    }
  };

  const handleResolveProblem = async () => {
    setAiLoading(true);
    try {
      const res = await fetch(`${API_BASE}/tickets/${problemId}/resolve`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Resolving ticket failed.");
      await fetchWorkspace();
      showToast('Ticket resolved and indexed in semantic memory!', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to resolve ticket.', 'error');
    } finally {
      setAiLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: '1rem' }}>
        <Loader2 size={40} className="pulse-dots" style={{ color: 'var(--color-primary)' }} />
        <span>Syncing ticket agent nodes...</span>
      </div>
    );
  }

  if (error || !problem) {
    return (
      <div className="app-container" style={{ textAlign: 'center', padding: '3rem' }}>
        <AlertTriangle size={48} color="red" style={{ marginBottom: '1rem' }} />
        <h3>Ticket Sync Offline</h3>
        <p style={{ color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>{error || "Unknown error occurred"}</p>
        <button onClick={() => navigate('/')} className="glass-btn glass-btn-secondary" style={{ marginTop: '1.5rem' }}>
          <ArrowLeft size={16} />
          <span>Return to Dashboard</span>
        </button>
      </div>
    );
  }

  // Parse diagnoses fields
  let rootCauses: string[] = [];
  let swot: { strengths: string[], weaknesses: string[], opportunities: string[], threats: string[] } = {
    strengths: [], weaknesses: [], opportunities: [], threats: []
  };
  let firstPrinciples: string[] = [];

  if (problem.diagnoses && problem.diagnoses.length > 0) {
    const diag = problem.diagnoses[0];
    try { rootCauses = JSON.parse(diag.root_causes || '[]'); } catch(e){}
    try { swot = JSON.parse(diag.swot_analysis || '{}'); } catch(e){}
    try { firstPrinciples = JSON.parse(diag.first_principles || '[]'); } catch(e){}
  }

  // Calculations for tasks checklist
  const totalTasks = problem.tasks.length;
  const completedTasks = problem.tasks.filter(t => t.status === 'Done').length;
  const taskProgressPct = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  return (
    <div className="app-container animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      
      {/* Workspace Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button onClick={() => navigate('/')} className="glass-btn glass-btn-secondary" style={{ padding: '0.5rem' }}>
            <ArrowLeft size={18} />
          </button>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '0.25rem' }}>
              <span className="badge badge-indigo">{problem.category}</span>
              <span className="badge badge-amber">{problem.urgency} Priority</span>
              <span className="badge badge-teal" style={{ textTransform: 'uppercase' }}>Status: {problem.status}</span>
            </div>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 800 }}>{problem.title}</h1>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {/* Export Button */}
          <button
            onClick={handleExportReport}
            className="glass-btn glass-btn-secondary"
            style={{ padding: '0.5rem 0.85rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
          >
            <Download size={14} />
            <span>Export Report</span>
          </button>

          {/* Global Agent Button Indicator */}
          {aiLoading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(255, 255, 255, 0.08)', padding: '0.5rem 1rem', borderRadius: '10px', border: '1px solid var(--border-color-glow)' }}>
              <Loader2 size={16} className="pulse-dots" style={{ color: 'var(--color-primary)' }} />
              <span style={{ fontSize: '0.85rem', color: '#e5e5e5', fontWeight: 600 }}>Agents Orchestrating...</span>
            </div>
          )}
        </div>
      </div>

      {/* Main split: Problem Statement Details vs Workspace Stages */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2.5fr', gap: '2rem', alignItems: 'start' }}>
        
        {/* Left Side: Original Problem Intake File Info */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div className="glass-card-static">
            <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Compass size={16} color="var(--color-secondary)" />
              <span>Ticket Summary</span>
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', lineHeight: '1.5', whiteSpace: 'pre-line' }}>
              {problem.description}
            </p>
          </div>

          {/* RAG memory card on active plan page */}
          {(problem.status === 'Execution' || problem.status === 'Resolved' || problem.status === 'Open') && (
            <div className="glass-card-static" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <h3 style={{ fontSize: '1rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <BookOpen size={16} color="var(--color-accent)" />
                <span>AI Knowledge Base Matches</span>
              </h3>
              
              {similarCases.length === 0 ? (
                <p style={{ fontSize: '0.8rem', color: 'var(--color-text-dark)' }}>
                  No similar solved cases in vector DB memory yet. Indexing happens once tickets are Resolved.
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.25rem' }}>
                  {similarCases.map((c, idx) => (
                    <div key={c.id} style={{
                      padding: '0.75rem',
                      background: 'rgba(255,255,255,0.02)',
                      border: '1px solid rgba(255,255,255,0.05)',
                      borderRadius: '8px',
                      fontSize: '0.8rem'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-secondary)', fontWeight: 600, marginBottom: '0.25rem' }}>
                        <span>Similar Case #{idx + 1}</span>
                        <span>{Math.round(c.similarity * 100)}% match</span>
                      </div>
                      <p style={{ color: 'var(--color-text-main)', fontWeight: 500, marginBottom: '0.25rem' }}>{c.problem_summary}</p>
                      <p style={{ color: 'var(--color-text-muted)', fontStyle: 'italic' }}>{c.solution_summary}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Side: Active Workspace Stage Panel */}
        <div style={{ minHeight: '400px' }}>
          
          {/* STAGE 1: Intake & Clarification */}
          {(problem.status === 'Intake' || problem.status === 'Clarifying' || problem.status === 'Awaiting Clarification') && (
            <div className="glass-card-static" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                <div style={{ background: 'rgba(255, 255, 255, 0.06)', padding: '0.625rem', borderRadius: '10px', color: 'var(--color-secondary)' }}>
                  <HelpCircle size={24} />
                </div>
                <div>
                  <h2 style={{ fontSize: '1.3rem', fontWeight: 700 }}>AI Clarifier Questions</h2>
                  <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem', marginTop: '0.15rem' }}>
                    The AI Clarifier needs more information to triage this ticket. Please answer the questions below.
                  </p>
                </div>
              </div>

              {problem.clarifications.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '2rem 1rem' }}>
                  <button 
                    onClick={handleGenerateClarifications}
                    disabled={aiLoading}
                    className="glass-btn glass-btn-primary"
                    style={{ fontSize: '1rem', padding: '1rem 2rem' }}
                  >
                    <Cpu size={18} />
                    <span>Ask Clarifying Questions</span>
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                  {problem.clarifications.map((q, idx) => (
                    <div key={q.id} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      <label style={{ fontSize: '0.9rem', color: '#e2e8f0', fontWeight: 600 }}>
                        {idx + 1}. {q.question}
                      </label>
                      <input
                        type="text"
                        placeholder="Provide details..."
                        value={answers[q.id] || ''}
                        onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
                        disabled={aiLoading || (problem.status !== 'Clarifying' && problem.status !== 'Awaiting Clarification')}
                        className="glass-input"
                      />
                    </div>
                  ))}

                  {(problem.status === 'Clarifying' || problem.status === 'Awaiting Clarification') && (
                    <button
                      onClick={handleSubmitAnswers}
                      disabled={aiLoading}
                      className="glass-btn glass-btn-primary"
                      style={{ alignSelf: 'flex-end', marginTop: '0.5rem' }}
                    >
                      <Play size={16} />
                      <span>Submit Answers & Progress</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* STAGE 2: Diagnosing */}
          {(problem.status === 'Diagnosing' || problem.status === 'Open') && (
            <div className="glass-card-static" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                <div style={{ background: 'rgba(255, 255, 255, 0.08)', padding: '0.625rem', borderRadius: '10px', color: 'var(--color-accent)' }}>
                  <Layers size={24} />
                </div>
                <div>
                  <h2 style={{ fontSize: '1.3rem', fontWeight: 700 }}>AI Triage Decision</h2>
                  <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem', marginTop: '0.15rem' }}>
                    The AI agent evaluates policy documents and tickets to recommend resolutions.
                  </p>
                </div>
              </div>

              {problem.diagnoses.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
                  <button 
                    onClick={handleRunDiagnosis}
                    disabled={aiLoading}
                    className="glass-btn glass-btn-primary"
                    style={{ fontSize: '1rem', padding: '1rem 2rem' }}
                  >
                    <Cpu size={18} />
                    <span>Run AI Triage Agent</span>
                  </button>

                  {/* Live Agent Step Timeline — shown while streaming */}
                  {agentSteps.length > 0 && (
                    <div style={{
                      marginTop: '1.25rem',
                      background: 'rgba(0, 0, 0, 0.6)',
                      border: '1px solid rgba(255, 255, 255, 0.12)',
                      borderRadius: '12px',
                      padding: '1rem 1.25rem',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.6rem'
                    }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--color-primary)', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                        🤖 LangGraph Agent Pipeline
                      </div>
                      {agentSteps.map((s, idx) => {
                        const stepLabel: Record<string, string> = {
                          retrieval: '🔍 Knowledge Base Retrieval',
                          evaluator: '⚖️ Evaluator',
                          writer: '✍️ Writer',
                          auditor: '🔎 Auditor',
                          clarify: '❓ Clarify',
                          escalate: '🚨 Escalate',
                          complete: '✅ Complete',
                        };
                        const isRunning = s.status === 'running';
                        const isDone = s.status === 'done';
                        return (
                          <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.875rem' }}>
                            <span style={{
                              width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0,
                              background: isRunning ? 'var(--color-primary)' : isDone ? '#10b981' : '#6b7280',
                              boxShadow: isRunning ? '0 0 8px var(--color-primary)' : 'none',
                              animation: isRunning ? 'pulse 1s ease-in-out infinite' : 'none',
                            }} />
                            <span style={{ color: isDone ? '#d1fae5' : 'var(--color-text-muted)', fontWeight: isRunning ? 600 : 400 }}>
                              {stepLabel[s.step] || s.step}
                              {s.decision ? ` → ${s.decision}` : ''}
                              {s.detail ? ` — ${s.detail}` : ''}
                              {s.passed === false ? ' ↻ Retrying...' : ''}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                  
                  {/* 5 Whys */}
                  <div>
                    <h3 style={{ fontSize: '1.1rem', color: '#fff', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <Activity size={16} color="var(--color-primary)" />
                      <span>AI Reasoning Chain</span>
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', paddingLeft: '0.5rem' }}>
                      {rootCauses.map((cause, idx) => (
                        <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                          <span style={{
                            background: idx === rootCauses.length - 1 ? 'var(--color-primary)' : 'rgba(255,255,255,0.05)',
                            color: idx === rootCauses.length - 1 ? '#fff' : 'var(--color-text-muted)',
                            width: '24px',
                            height: '24px',
                            borderRadius: '50%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            flexShrink: 0
                          }}>
                            {idx + 1}
                          </span>
                          <span style={{
                            fontSize: '0.9rem', 
                            color: idx === rootCauses.length - 1 ? '#fff' : 'var(--color-text-muted)',
                            fontWeight: idx === rootCauses.length - 1 ? 600 : 400
                          }}>
                            {cause}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* SWOT Grid */}
                  <div>
                    <h3 style={{ fontSize: '1.1rem', color: '#fff', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <Layers size={16} color="var(--color-secondary)" />
                      <span>Knowledge Match Assessment</span>
                    </h3>
                    <div className="swot-matrix">
                      <div className="swot-box swot-s">
                        <h4 style={{ color: 'var(--color-success)', fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.5rem' }}>STRENGTHS</h4>
                        <ul style={{ paddingLeft: '1.1rem', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                          {swot.strengths?.map((item, i) => <li key={i} style={{ marginBottom: 4 }}>{item}</li>)}
                        </ul>
                      </div>
                      <div className="swot-box swot-w">
                        <h4 style={{ color: 'var(--color-danger)', fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.5rem' }}>WEAKNESSES</h4>
                        <ul style={{ paddingLeft: '1.1rem', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                          {swot.weaknesses?.map((item, i) => <li key={i} style={{ marginBottom: 4 }}>{item}</li>)}
                        </ul>
                      </div>
                      <div className="swot-box swot-o">
                        <h4 style={{ color: 'var(--color-secondary)', fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.5rem' }}>OPPORTUNITIES</h4>
                        <ul style={{ paddingLeft: '1.1rem', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                          {swot.opportunities?.map((item, i) => <li key={i} style={{ marginBottom: 4 }}>{item}</li>)}
                        </ul>
                      </div>
                      <div className="swot-box swot-t">
                        <h4 style={{ color: 'var(--color-warning)', fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.5rem' }}>THREATS</h4>
                        <ul style={{ paddingLeft: '1.1rem', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                          {swot.threats?.map((item, i) => <li key={i} style={{ marginBottom: 4 }}>{item}</li>)}
                        </ul>
                      </div>
                    </div>
                  </div>

                  {/* First Principles */}
                  <div>
                    <h3 style={{ fontSize: '1.1rem', color: '#fff', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <Lightbulb size={16} color="var(--color-warning)" />
                      <span>Key Policy Extraction</span>
                    </h3>
                    <ul style={{ paddingLeft: '1.25rem', fontSize: '0.9rem', color: 'var(--color-text-muted)', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {firstPrinciples.map((item, i) => (
                        <li key={i} style={{ lineHeight: '1.4' }}>{item}</li>
                      ))}
                    </ul>
                  </div>

                  {/* Action trigger */}
                  <button
                    onClick={handleGenerateSolutions}
                    disabled={aiLoading}
                    className="glass-btn glass-btn-primary"
                    style={{ alignSelf: 'flex-end', marginTop: '1rem' }}
                  >
                    <Play size={16} />
                    <span>Generate Draft Resolutions</span>
                  </button>

                </div>
              )}
            </div>
          )}

          {/* STAGE 3: Planning & Comparing Solutions */}
          {problem.status === 'Planning' && (
            <div className="glass-card-static" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                <div style={{ background: 'rgba(255, 255, 255, 0.08)', padding: '0.625rem', borderRadius: '10px', color: 'var(--color-primary)' }}>
                  <Award size={24} />
                </div>
                <div>
                  <h2 style={{ fontSize: '1.3rem', fontWeight: 700 }}>Suggested Resolutions</h2>
                  <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem', marginTop: '0.15rem' }}>
                    Select the most accurate drafted support resolution for this ticket.
                  </p>
                </div>
              </div>

              {problem.solutions.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
                  <button 
                    onClick={handleGenerateSolutions}
                    disabled={aiLoading}
                    className="glass-btn glass-btn-primary"
                    style={{ fontSize: '1rem', padding: '1rem 2rem' }}
                  >
                    <Cpu size={18} />
                    <span>Generate Suggested Resolutions</span>
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  
                  {/* Solution Options Cards */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {problem.solutions.map((sol) => (
                      <div 
                        key={sol.id} 
                        className="glass-card" 
                        onClick={() => handleSelectSolution(sol.id)}
                        style={{
                          cursor: 'pointer',
                          borderColor: sol.selected ? 'var(--color-primary)' : 'var(--border-color)',
                          boxShadow: sol.selected ? '0 0 15px rgba(99,102,241,0.15)' : 'var(--shadow-sm)',
                          background: sol.selected ? 'rgba(99,102,241,0.03)' : 'var(--bg-surface)'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', marginBottom: '0.5rem' }}>
                          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                            <span style={{
                              width: '18px',
                              height: '18px',
                              borderRadius: '50%',
                              border: '2px solid',
                              borderColor: sol.selected ? 'var(--color-primary)' : 'var(--color-text-dark)',
                              display: 'inline-flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              flexShrink: 0
                            }}>
                              {sol.selected && <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-primary)' }} />}
                            </span>
                            <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: sol.selected ? '#fff' : 'rgba(255,255,255,0.85)' }}>{sol.title}</h3>
                          </div>
                          
                          {/* Leaderboard Score */}
                          <div style={{ textAlign: 'right' }}>
                            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-dark)', fontWeight: 600 }}>RATING</span>
                            <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--color-secondary)' }}>
                              {(sol.score * 10).toFixed(0)}%
                            </div>
                          </div>
                        </div>

                        <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', lineHeight: '1.45', marginBottom: '1rem' }}>
                          {sol.strategy_details}
                        </p>

                        {/* Scores breakdowns */}
                        <div style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(3, 1fr)',
                          gap: '0.75rem',
                          background: 'rgba(0,0,0,0.2)',
                          padding: '0.75rem',
                          borderRadius: '8px',
                          fontSize: '0.8rem',
                          color: 'var(--color-text-muted)'
                        }}>
                          <div>
                            <span style={{ color: 'var(--color-text-dark)' }}>Impact: </span>
                            <span style={{ fontWeight: 600, color: 'var(--color-success)' }}>{sol.impact}/10</span>
                          </div>
                          <div>
                            <span style={{ color: 'var(--color-text-dark)' }}>Confidence: </span>
                            <span style={{ fontWeight: 600, color: 'var(--color-secondary)' }}>{sol.confidence}/10</span>
                          </div>
                          <div>
                            <span style={{ color: 'var(--color-text-dark)' }}>Risk Level: </span>
                            <span style={{ fontWeight: 600, color: 'var(--color-danger)' }}>{sol.risk}/10</span>
                          </div>
                        </div>
                        
                        {sol.constraints && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-dark)', marginTop: '0.5rem', fontStyle: 'italic' }}>
                            Constraint: {sol.constraints}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Actions */}
                  <button
                    onClick={handleGeneratePlan}
                    disabled={aiLoading || !problem.solutions.some(s => s.selected)}
                    className="glass-btn glass-btn-primary"
                    style={{ alignSelf: 'flex-end', marginTop: '1rem' }}
                  >
                    <Play size={16} />
                    <span>Compile Action Checklist</span>
                  </button>

                </div>
              )}
            </div>
          )}

          {/* STAGE 4: Execution & Checklist Tracker */}
          {problem.status === 'Execution' && (
            <div className="glass-card-static" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1fr' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                  <div style={{ background: 'rgba(255, 255, 255, 0.06)', padding: '0.625rem', borderRadius: '10px', color: 'var(--color-secondary)' }}>
                    <ListTodo size={24} />
                  </div>
                  <div>
                    <h2 style={{ fontSize: '1.3rem', fontWeight: 700 }}>Resolution Actions & Checklist</h2>
                    <p style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem', marginTop: '0.15rem' }}>
                      Follow these steps to apply the resolution. Mark each task completed to close the ticket.
                    </p>
                  </div>
                </div>
              </div>

              {/* Progress metrics */}
              <div style={{
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid var(--border-color)',
                borderRadius: '12px',
                padding: '1rem'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                  <span style={{ color: 'var(--color-text-muted)' }}>Tasks Resolved: {completedTasks} / {totalTasks}</span>
                  <span style={{ fontWeight: 600, color: 'var(--color-secondary)' }}>{taskProgressPct}% Complete</span>
                </div>
                <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: `${taskProgressPct}%`, height: '100%', background: 'linear-gradient(to right, var(--color-primary), var(--color-secondary))', borderRadius: '4px', transition: 'width 0.3s ease' }} />
                </div>
              </div>

              {/* Task Items List */}
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {problem.tasks.map((t) => {
                  const isDone = t.status === 'Done';
                  return (
                    <div 
                      key={t.id}
                      onClick={() => handleToggleTask(t.id, t.status)}
                      className={`task-item ${isDone ? 'task-checked' : ''}`}
                      style={{ cursor: 'pointer' }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span style={{
                          color: isDone ? 'var(--color-success)' : 'var(--color-text-dark)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0
                        }}>
                          <CheckSquare size={20} fill={isDone ? 'rgba(16, 185, 129, 0.15)' : 'none'} />
                        </span>
                        
                        <div>
                          <span style={{ fontSize: '0.9rem', color: isDone ? 'var(--color-text-dark)' : '#fff' }}>
                            {t.title}
                          </span>
                          
                          {t.timeline && (
                            <span style={{
                              display: 'inline-block',
                              marginLeft: '0.5rem',
                              fontSize: '0.75rem',
                              color: 'var(--color-text-dark)'
                            }}>
                              ({t.timeline})
                            </span>
                          )}
                        </div>
                      </div>
                      
                      <span className={`badge ${
                        t.priority === 'High' ? 'badge-rose' : (t.priority === 'Medium' ? 'badge-amber' : 'badge-teal')
                      }`}>
                        {t.priority}
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* Resolution Action */}
              <button
                onClick={handleResolveProblem}
                disabled={aiLoading}
                className="glass-btn glass-btn-primary"
                style={{
                  alignSelf: 'center',
                  marginTop: '1rem',
                  background: 'linear-gradient(135deg, var(--color-success) 0%, var(--color-secondary) 100%)',
                  boxShadow: '0 4px 15px rgba(16, 185, 129, 0.25)'
                }}
              >
                <CheckCircle size={16} />
                <span>Mark Ticket Resolved & Index</span>
              </button>
            </div>
          )}

          {/* STAGE 5: Resolved */}
          {problem.status === 'Resolved' && (
            <div className="glass-card-static" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1.5rem', textAlign: 'center', padding: '3rem 2rem' }}>
              <div style={{
                background: 'rgba(16, 185, 129, 0.1)',
                color: 'var(--color-success)',
                padding: '1rem',
                borderRadius: '50%',
                display: 'inline-flex',
                boxShadow: '0 0 25px rgba(16, 185, 129, 0.25)'
              }}>
                <Award size={48} />
              </div>
              
              <div>
                <h2 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#fff' }}>Support Ticket Resolved</h2>
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', marginTop: '0.5rem', maxWidth: '400px' }}>
                  This support ticket is marked as Resolved. The ticket inquiry and final resolution have been indexed in the pgvector database for future reference.
                </p>
              </div>

              {/* Memory Summary index report */}
              <div style={{
                background: 'rgba(0,0,0,0.2)',
                border: '1px solid var(--border-color)',
                borderRadius: '12px',
                padding: '1rem',
                textAlign: 'left',
                width: '100%',
                fontSize: '0.85rem',
                color: 'var(--color-text-muted)'
              }}>
                <div style={{ fontWeight: 600, color: '#fff', marginBottom: '0.5rem' }}>Indexed Vector Schema:</div>
                <div style={{ marginBottom: 4 }}><span style={{ color: 'var(--color-primary)' }}>Vector ID: </span> {problemId}</div>
                <div style={{ marginBottom: 4 }}><span style={{ color: 'var(--color-primary)' }}>Index Name: </span> memories</div>
                <div><span style={{ color: 'var(--color-primary)' }}>Dimensions: </span> 128 normalized</div>
              </div>

              <button onClick={() => navigate('/')} className="glass-btn glass-btn-secondary" style={{ marginTop: '1rem' }}>
                <ArrowLeft size={16} />
                <span>Return to Dashboard</span>
              </button>
            </div>
          )}

          {/* STAGE: Escalated */}
          {problem.status === 'Escalated' && (
            <div className="glass-card-static" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1.5rem', textAlign: 'center', padding: '3rem 2rem' }}>
              <div style={{
                background: 'rgba(239, 68, 68, 0.1)',
                color: '#f87171',
                padding: '1rem',
                borderRadius: '50%',
                display: 'inline-flex',
                boxShadow: '0 0 25px rgba(239, 68, 68, 0.25)'
              }}>
                <AlertTriangle size={48} />
              </div>
              
              <div>
                <h2 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#fff' }}>Ticket Escalated to Human</h2>
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', marginTop: '0.5rem', maxWidth: '400px' }}>
                  This ticket has been escalated to a senior support representative. A human agent will contact you via email shortly.
                </p>
              </div>

              <button onClick={() => navigate('/')} className="glass-btn glass-btn-secondary" style={{ marginTop: '1rem' }}>
                <ArrowLeft size={16} />
                <span>Return to Dashboard</span>
              </button>
            </div>
          )}

        </div>
      </div>

      {/* Collapsible Activity Log */}
      <div className="glass-card-static" style={{ marginTop: '0.5rem' }}>
        <button
          onClick={() => setActivityOpen(!activityOpen)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--color-text-main)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            width: '100%',
            cursor: 'pointer',
            fontFamily: 'var(--font-title)',
            fontSize: '1.1rem',
            fontWeight: 600,
            padding: 0,
          }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Clock size={18} color="var(--color-accent)" />
            Activity Log
            <span className="badge badge-violet" style={{ fontSize: '0.65rem' }}>{activityLog.length}</span>
          </span>
          {activityOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>

        {activityOpen && (
          <div style={{ marginTop: '1rem' }}>
            {activityLog.length === 0 ? (
              <p style={{ color: 'var(--color-text-dark)', fontSize: '0.85rem' }}>No activity recorded yet.</p>
            ) : (
              <div className="activity-timeline">
                {activityLog.map(entry => (
                  <div key={entry.id} className="activity-item">
                    <div className="activity-dot" />
                    <div className="activity-action">{entry.action}</div>
                    {entry.detail && <div className="activity-detail">{entry.detail}</div>}
                    <div className="activity-time">{new Date(entry.created_at).toLocaleString()}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Workspace;
