import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Link2, Mail, Plus, Trash2, RefreshCw,
  CheckCircle, AlertCircle, Loader2,
} from 'lucide-react';
import { listConnections, startConnection, deleteConnection, syncConnection } from '../api';

/* ── Demo data ─────────────────────────────────────────── */
const PROVIDERS = [
  {
    id: 'gmail',
    name: 'Gmail',
    description: 'Connect your Gmail inbox to auto-scan incoming emails for phishing threats',
    Icon: Mail,
    available: true,
  },
  {
    id: 'outlook',
    name: 'Outlook / M365',
    description: 'Connect Microsoft Outlook for continuous monitoring',
    Icon: Mail,
    available: false,
  },
  {
    id: 'slack',
    name: 'Slack',
    description: 'Scan suspicious links shared in Slack channels',
    Icon: Link2,
    available: false,
  },
];

export default function ConnectionsPage() {
  const [connections, setConnections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncingId, setSyncingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [connectingId, setConnectingId] = useState(null);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    loadConnections();
  }, []);

  async function loadConnections() {
    try {
      const data = await listConnections();
      setConnections(data || []);
    } catch {
      setConnections([]);
    }
    setLoading(false);
  }

  function showToast(type, message) {
    setToast({ type, message });
    setTimeout(() => setToast(null), 3000);
  }

  async function handleConnect(provider) {
    setConnectingId(provider);
    try {
      const data = await startConnection(provider);
      if (data.redirect_url) {
        window.location.href = data.redirect_url;
      }
    } catch (err) {
      showToast('error', err.message || `Failed to connect ${provider}`);
    }
    setConnectingId(null);
  }

  async function handleSync(id) {
    setSyncingId(id);
    try {
      const data = await syncConnection(id);
      showToast('success', `Synced ${data.messages_pulled} messages → ${data.scans_initiated?.length || 0} new scans`);
    } catch (err) {
      showToast('error', err.message || 'Sync failed');
    }
    setSyncingId(null);
  }

  async function handleDelete(id) {
    if (!confirm('Revoke this connection?')) return;
    setDeletingId(id);
    try {
      await deleteConnection(id);
      setConnections(prev => prev.filter(c => c.id !== id));
      showToast('success', 'Connection revoked');
    } catch (err) {
      showToast('error', err.message || 'Failed to delete');
    }
    setDeletingId(null);
  }

  const connectedProviders = new Set(connections.map(c => c.provider));

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-1" style={{ color: 'var(--color-text-primary)' }}>Connections</h1>
      <p className="text-sm mb-8" style={{ color: 'var(--color-text-secondary)' }}>
        Link external accounts to automatically scan incoming threats
      </p>

      {/* ── Toast ──────────────────────────────────────── */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ y: -10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -10, opacity: 0 }}
            className="fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-2.5 rounded-lg font-mono text-xs"
            style={{
              backgroundColor: toast.type === 'success' ? 'var(--color-risk-low-bg)' : 'var(--color-risk-high-bg)',
              color: toast.type === 'success' ? 'var(--color-risk-low)' : 'var(--color-risk-high)',
              border: `1px solid ${toast.type === 'success' ? 'rgba(52,211,153,0.3)' : 'rgba(229,72,77,0.3)'}`,
            }}
          >
            {toast.type === 'success' ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
            {toast.message}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Active Connections ─────────────────────────── */}
      {connections.length > 0 && (
        <>
          <span className="section-label block mb-4">Active Connections</span>
          <div className="flex flex-col gap-3 mb-10">
            {connections.map((conn, i) => (
              <motion.div
                key={conn.id}
                initial={{ x: -15, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: i * 0.05 }}
                className="card flex items-center gap-4"
                style={{ padding: '1rem 1.25rem' }}
              >
                <div
                  className="flex items-center justify-center rounded-lg flex-shrink-0"
                  style={{ width: 40, height: 40, backgroundColor: 'var(--color-accent-dim)' }}
                >
                  <Mail size={18} style={{ color: 'var(--color-accent)' }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                    {conn.provider?.charAt(0).toUpperCase() + conn.provider?.slice(1)}
                  </p>
                  <p className="text-xs font-mono" style={{ color: 'var(--color-text-muted)' }}>
                    {conn.metadata?.email || conn.id.slice(0, 8)}
                    {conn.last_synced_at && ` · Last synced ${new Date(conn.last_synced_at).toLocaleDateString()}`}
                  </p>
                </div>
                <div
                  className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold"
                  style={{
                    backgroundColor: 'var(--color-risk-low-bg)',
                    color: 'var(--color-risk-low)',
                    border: '1px solid rgba(52,211,153,0.3)',
                  }}
                >
                  <CheckCircle size={10} /> Active
                </div>
                <div className="flex gap-1.5">
                  <button
                    onClick={() => handleSync(conn.id)}
                    disabled={syncingId === conn.id}
                    className="btn-outline"
                    style={{ padding: '6px 10px', fontSize: '10px' }}
                    title="Sync now"
                  >
                    {syncingId === conn.id ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
                  </button>
                  <button
                    onClick={() => handleDelete(conn.id)}
                    disabled={deletingId === conn.id}
                    className="btn-outline"
                    style={{
                      padding: '6px 10px', fontSize: '10px',
                      color: 'var(--color-risk-high)',
                      borderColor: 'rgba(229,72,77,0.3)',
                    }}
                    title="Revoke"
                  >
                    {deletingId === conn.id ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        </>
      )}

      {/* ── Available Providers ────────────────────────── */}
      <span className="section-label normal-case block mb-4">Available Integrations</span>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 integrations-grid">
        {PROVIDERS.map((p, i) => {
          const isConnected = connectedProviders.has(p.id);
          return (
            <motion.div
              key={p.id}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1 + i * 0.08 }}
              className="card card-hover flex flex-col"
              style={{ padding: '1.25rem' }}
            >
              <div className="flex items-center gap-3 mb-3">
                <div
                  className="flex items-center justify-center rounded-lg"
                  style={{
                    width: 36, height: 36,
                    backgroundColor: p.available ? 'var(--color-accent-dim)' : 'var(--color-surface-alt)',
                  }}
                >
                  <p.Icon size={16} style={{ color: p.available ? 'var(--color-accent)' : 'var(--color-text-muted)' }} />
                </div>
                <div>
                  <p className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>{p.name}</p>
                  {!p.available && (
                    <span className="pill pill-muted normal-case text-xs mt-1">Coming Soon</span>
                  )}
                </div>
              </div>
              <p className="text-xs leading-relaxed mb-4 flex-1" style={{ color: 'var(--color-text-secondary)' }}>
                {p.description}
              </p>
              <button
                onClick={() => handleConnect(p.id)}
                disabled={!p.available || isConnected || connectingId === p.id}
                className={isConnected ? 'btn-outline' : 'btn-primary'}
                style={{ width: '100%', justifyContent: 'center', padding: '8px', fontSize: '11px' }}
              >
                {connectingId === p.id ? (
                  <><Loader2 size={12} className="animate-spin" /> Connecting...</>
                ) : isConnected ? (
                  <><CheckCircle size={12} /> Connected</>
                ) : (
                  <><Plus size={12} /> Connect</>
                )}
              </button>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
