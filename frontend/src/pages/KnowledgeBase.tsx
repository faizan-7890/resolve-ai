import React, { useState, useEffect } from 'react';
import { useAuth, API_BASE } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import {
  Search, Trash2, Eye, BookOpen, Clock, Loader2, X, AlertTriangle
} from 'lucide-react';

interface Document {
  id: number;
  title: string;
  content: string;
  created_at: string;
  chunks_count: number;
}

const KnowledgeBase: React.FC = () => {
  const { token, user } = useAuth();
  const { showToast } = useToast();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null);
  const [deleting, setDeleting] = useState<boolean>(false);

  const fetchDocuments = async () => {
    try {
      const res = await fetch(`${API_BASE}/ingest/documents`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to fetch documents.");
      const data = await res.json();
      setDocuments(data);
    } catch (err: any) {
      showToast(err.message || "Failed to load knowledge base documents.", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [token]);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      const res = await fetch(`${API_BASE}/ingest/documents/${deleteTarget.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to delete document.");
      }
      showToast(`Document "${deleteTarget.title}" deleted successfully.`, "success");
      setDocuments(documents.filter(d => d.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err: any) {
      showToast(err.message || "Could not delete document.", "error");
    } finally {
      setDeleting(false);
    }
  };

  const filteredDocs = documents.filter(doc =>
    doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.content.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="app-container animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      
      {/* Page Title */}
      <div>
        <h1 style={{ fontSize: '2.2rem', fontWeight: 800, marginBottom: '0.5rem' }}>
          Knowledge Base Management
        </h1>
        <p style={{ color: 'var(--color-text-muted)' }}>
          Review, search, and manage corporate policy documents and FAQ resources parsed into vector embeddings.
        </p>
      </div>

      {/* Control bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
        <div style={{ position: 'relative', flex: 1, maxWidth: '400px' }}>
          <Search size={18} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-dark)' }} />
          <input
            type="text"
            placeholder="Search documents by title or text content..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="glass-input"
            style={{ paddingLeft: '2.5rem', width: '100%' }}
          />
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '40vh', gap: '1rem' }}>
          <Loader2 size={40} className="pulse-dots" style={{ color: 'var(--color-primary)' }} />
          <span>Syncing vector storage files...</span>
        </div>
      ) : filteredDocs.length === 0 ? (
        <div className="glass-card-static" style={{ textAlign: 'center', padding: '4rem 2rem', color: 'var(--color-text-muted)' }}>
          <BookOpen size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
          <h3>No Documents Found</h3>
          <p style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
            {searchQuery ? "No matches found for your search query." : "Ingest documents or upload files in Settings to populate the knowledge base."}
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.25rem' }}>
          {filteredDocs.map((doc) => (
            <div key={doc.id} className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', padding: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                  <div style={{ background: 'rgba(99, 102, 241, 0.1)', color: 'var(--color-primary)', padding: '0.5rem', borderRadius: '8px' }}>
                    <BookOpen size={20} />
                  </div>
                  <div>
                    <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff' }}>{doc.title}</h3>
                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginTop: '0.25rem', fontSize: '0.75rem', color: 'var(--color-text-dark)' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <Clock size={12} />
                        {new Date(doc.created_at).toLocaleDateString()}
                      </span>
                      <span className="badge badge-teal">{doc.chunks_count} Vector Chunks</span>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    onClick={() => setSelectedDoc(doc)}
                    className="glass-btn glass-btn-secondary"
                    style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                  >
                    <Eye size={14} />
                    <span>Preview</span>
                  </button>

                  {user?.role === 'admin' && (
                    <button
                      onClick={() => setDeleteTarget(doc)}
                      className="glass-btn glass-btn-danger"
                      style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                    >
                      <Trash2 size={14} />
                      <span>Delete</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Preview Snippet */}
              <p style={{
                fontSize: '0.85rem',
                color: 'var(--color-text-muted)',
                lineHeight: '1.5',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: '-webkit-box',
                WebkitLineClamp: 3,
                WebkitBoxOrient: 'vertical',
                background: 'rgba(0,0,0,0.15)',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                border: '1px solid rgba(255,255,255,0.03)'
              }}>
                {doc.content}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Preview Full Content Dialog */}
      {selectedDoc && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0, 0, 0, 0.7)',
          backdropFilter: 'blur(5px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: '2rem 1rem'
        }}>
          <div className="glass-card-static animate-fade-in" style={{
            maxWidth: '700px',
            width: '100%',
            maxHeight: '80vh',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.25rem',
            padding: '1.75rem',
            position: 'relative',
            overflow: 'hidden'
          }}>
            <button
              onClick={() => setSelectedDoc(null)}
              style={{ position: 'absolute', right: '1.25rem', top: '1.25rem', background: 'none', border: 'none', color: 'var(--color-text-dark)', cursor: 'pointer' }}
            >
              <X size={20} />
            </button>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                <span className="badge badge-teal">{selectedDoc.chunks_count} Chunks</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--color-text-dark)' }}>
                  Ingested on {new Date(selectedDoc.created_at).toLocaleString()}
                </span>
              </div>
              <h2 style={{ fontSize: '1.4rem', fontWeight: 800, paddingRight: '2rem' }}>{selectedDoc.title}</h2>
            </div>

            <div style={{
              flex: 1,
              overflowY: 'auto',
              background: 'rgba(0,0,0,0.2)',
              border: '1px solid var(--border-color)',
              padding: '1.25rem',
              borderRadius: '10px',
              fontSize: '0.9rem',
              lineHeight: '1.6',
              color: 'var(--color-text-main)',
              whiteSpace: 'pre-wrap'
            }}>
              {selectedDoc.content}
            </div>

            <button
              onClick={() => setSelectedDoc(null)}
              className="glass-btn glass-btn-secondary"
              style={{ alignSelf: 'flex-end' }}
            >
              Close Preview
            </button>
          </div>
        </div>
      )}

      {/* Delete Document Warning Dialog */}
      {deleteTarget && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0, 0, 0, 0.7)',
          backdropFilter: 'blur(5px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: '1rem'
        }}>
          <div className="glass-card-static animate-fade-in" style={{
            maxWidth: '450px',
            width: '100%',
            padding: '1.75rem',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1.25rem',
            position: 'relative'
          }}>
            <div style={{
              background: 'rgba(239, 68, 68, 0.1)',
              color: '#f87171',
              padding: '0.75rem',
              borderRadius: '50%',
              display: 'inline-flex'
            }}>
              <AlertTriangle size={32} />
            </div>

            <div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff' }}>Delete Document?</h3>
              <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', marginTop: '0.5rem', lineHeight: '1.5' }}>
                Are you sure you want to delete <strong>"{deleteTarget.title}"</strong>?<br/>
                This action is irreversible. All <strong>{deleteTarget.chunks_count}</strong> associated vector database chunks and embeddings will be permanently destroyed.
              </p>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', width: '100%', marginTop: '0.25rem' }}>
              <button
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
                className="glass-btn glass-btn-secondary"
                style={{ flex: 1 }}
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="glass-btn glass-btn-danger"
                style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.25rem' }}
              >
                {deleting ? (
                  <>
                    <Loader2 size={14} className="pulse-dots" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <Trash2 size={14} />
                    <span>Delete Permanently</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default KnowledgeBase;
