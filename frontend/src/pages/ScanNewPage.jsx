import { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mail, Globe, QrCode, Image, Upload, Send,
  CheckCircle, Loader2, AlertCircle,
} from 'lucide-react';
import { submitScan, getScan, connectScanSocket } from '../api';

const tabs = [
  { key: 'email', label: 'Paste Email', Icon: Mail },
  { key: 'url', label: 'Paste URL', Icon: Globe },
  { key: 'screenshot', label: 'Upload Screenshot', Icon: Image },
  { key: 'qr', label: 'Upload QR', Icon: QrCode },
];

const layerLabels = [
  { layer: 0, label: 'Normalize', desc: 'Unshortening URLs, decoding payloads' },
  { layer: 1, label: 'Deterministic Rules', desc: 'Typosquatting, TLDs, subdomains' },
  { layer: 2, label: 'Behavioral Analysis', desc: 'Social engineering triggers' },
  { layer: 3, label: 'Risk Scoring', desc: 'Deterministic weighted aggregation' },
  { layer: 4, label: 'AI Explanation', desc: 'Generating evidence narrative' },
];

export default function ScanNewPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('email');
  const [content, setContent] = useState('');
  const [file, setFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [scanId, setScanId] = useState(null);
  const [layerStates, setLayerStates] = useState({});
  const [finalResult, setFinalResult] = useState(null);
  const [error, setError] = useState('');
  const wsRef = useRef(null);
  const fileInputRef = useRef(null);

  const isFileTab = activeTab === 'screenshot' || activeTab === 'qr';

  function handleFileChange(e) {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  }

  function handleDrop(e) {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) setFile(f);
  }

  const handleWsMessage = useCallback((data) => {
    if (data.layer !== undefined) {
      setLayerStates(prev => ({ ...prev, [data.layer]: data }));
    }
    if (data.status === 'complete' && data.risk_score !== undefined) {
      setFinalResult(data);
    }
    if (data.status === 'failed') {
      setError(data.error || 'Scan failed');
    }
  }, []);

  async function handleSubmit() {
    if (!content.trim() && !file) return;
    setError('');
    setSubmitting(true);
    setLayerStates({});
    setFinalResult(null);

    try {
      const payload = { source_type: activeTab, content: content || undefined };
      const data = await submitScan(payload);
      const sid = data.scan_id;
      setScanId(sid);

      // Connect WebSocket for live progress
      wsRef.current = connectScanSocket(sid, handleWsMessage);

      // Also poll for completion as fallback
      let attempts = 0;
      const poller = setInterval(async () => {
        attempts++;
        if (attempts > 30 || finalResult) {
          clearInterval(poller);
          return;
        }
        try {
          const scan = await getScan(sid);
          if (scan.status === 'completed' || scan.status === 'failed') {
            clearInterval(poller);
            setFinalResult({
              scan_id: sid,
              risk_score: scan.risk_score,
              severity: scan.severity,
              status: scan.status,
            });
            // Fill remaining layers as complete
            for (let l = 0; l <= 4; l++) {
              setLayerStates(prev => prev[l] ? prev : { ...prev, [l]: { status: 'complete', layer: l } });
            }
          }
        } catch {}
      }, 2000);
    } catch (err) {
      setError(err.message || 'Failed to submit scan');
      setSubmitting(false);
    }
  }

  // Navigate to result on completion
  useEffect(() => {
    if (finalResult && scanId) {
      const timer = setTimeout(() => navigate(`/scan/${scanId}`), 1500);
      return () => clearTimeout(timer);
    }
  }, [finalResult, scanId, navigate]);

  // Cleanup WS on unmount
  useEffect(() => () => wsRef.current?.close(), []);

  const isScanning = submitting && scanId && !finalResult;

  return (
    <div className="max-w-2xl mx-auto px-6 py-8 flex flex-col gap-6">
      {/* ── Header ─────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold mb-1" style={{ color: 'var(--color-text-primary)' }}>New Scan</h1>
        <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
          Submit suspicious content for 5-layer threat analysis
        </p>
      </div>

      {/* ── Tabs ────────────────────────────────────────── */}
      {!isScanning && !finalResult && (
        <div className="flex flex-col gap-6">
          <div className="flex gap-1 rounded-xl" style={{ backgroundColor: 'var(--color-surface)' }}>
            {tabs.map(t => (
              <button
                key={t.key}
                onClick={() => { setActiveTab(t.key); setContent(''); setFile(null); setError(''); }}
                className="flex items-center gap-1.5 flex-1 justify-center py-2.5 rounded-lg font-mono text-xs font-medium border-none cursor-pointer transition-colors"
                style={{
                  backgroundColor: activeTab === t.key ? 'var(--color-accent-dim)' : 'transparent',
                  color: activeTab === t.key ? 'var(--color-accent)' : 'var(--color-text-muted)',
                }}
              >
                <t.Icon size={13} />
                {t.label}
              </button>
            ))}
          </div>

          {/* ── Input Area ──────────────────────────────────── */}
          <div>
            {isFileTab ? (
              <div
                onClick={() => fileInputRef.current?.click()}
                onDrop={handleDrop}
                onDragOver={e => e.preventDefault()}
                className="flex flex-col items-center justify-center py-12 rounded-lg cursor-pointer transition-colors"
                style={{
                  border: '2px dashed var(--color-border)',
                  backgroundColor: file ? 'var(--color-accent-dim)' : 'var(--color-surface)',
                }}
              >
                <Upload size={28} style={{ color: file ? 'var(--color-accent)' : 'var(--color-text-muted)', marginBottom: 8 }} />
                <p className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                  {file ? file.name : `Drop or click to upload ${activeTab === 'qr' ? 'QR code' : 'screenshot'}`}
                </p>
                <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileChange} hidden />
              </div>
            ) : (
              <textarea
                rows={activeTab === 'url' ? 3 : 12}
                placeholder={
                  activeTab === 'url'
                    ? 'Paste a suspicious URL (e.g. https://paypa1.com/verify)'
                    : 'Paste suspicious email content here...\n\nInclude headers, body text, and any embedded links.'
                }
                value={content}
                onChange={e => setContent(e.target.value)}
                className="font-mono text-sm"
                style={{ resize: 'vertical', minHeight: activeTab === 'url' ? 80 : 300 }}
              />
            )}
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-mono"
              style={{ backgroundColor: 'var(--color-risk-high-bg)', color: 'var(--color-risk-high)', border: '1px solid rgba(229,72,77,0.3)' }}
            >
              <AlertCircle size={14} /> {error}
            </div>
          )}

          <button
            onClick={handleSubmit}
            disabled={(!content.trim() && !file) || submitting}
            className="btn-primary w-full justify-center"
            style={{ padding: '12px' }}
          >
            {submitting ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            {submitting ? 'Analyzing...' : 'Analyze Content'}
          </button>
        </div>
      )}

      {/* ── Live Progress ──────────────────────────────── */}
      {(isScanning || finalResult) && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="card"
          style={{ padding: '1.5rem' }}
        >
          <span className="section-label block mb-5">Pipeline Progress</span>
          <div className="flex flex-col gap-3">
            {layerLabels.map(({ layer, label, desc }) => {
              const state = layerStates[layer];
              const isComplete = state?.status === 'complete';
              const isRunning = state?.status === 'running';
              const isPending = !state;

              let dotColor = 'var(--color-text-muted)';
              if (isComplete) dotColor = 'var(--color-accent)';
              if (isRunning) dotColor = 'var(--color-accent)';

              return (
                <motion.div
                  key={layer}
                  initial={{ x: -10, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  transition={{ delay: layer * 0.1 }}
                  className="flex items-center gap-3"
                >
                  {/* Status indicator */}
                  <div className="flex-shrink-0" style={{ width: 24, textAlign: 'center' }}>
                    {isComplete ? (
                      <CheckCircle size={18} style={{ color: 'var(--color-accent)' }} />
                    ) : isRunning ? (
                      <Loader2 size={18} style={{ color: 'var(--color-accent)' }} className="animate-spin" />
                    ) : (
                      <div
                        className="rounded-full mx-auto"
                        style={{ width: 10, height: 10, backgroundColor: 'var(--color-text-muted)', opacity: 0.3 }}
                      />
                    )}
                  </div>

                  {/* Label */}
                  <div className="flex-1">
                    <p className="font-mono text-xs font-semibold" style={{
                      color: isComplete || isRunning ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
                    }}>
                      Layer {layer}: {label}
                    </p>
                    <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{desc}</p>
                  </div>

                  {/* Badge */}
                  {isComplete && state.evidence_count !== undefined && (
                    <span className="pill" style={{ color: 'var(--color-accent)', borderColor: 'rgba(200,255,51,0.2)' }}>
                      {state.evidence_count} findings
                    </span>
                  )}
                  {isComplete && state.risk_score !== undefined && (
                    <span className="pill" style={{
                      color: state.severity === 'HIGH' ? 'var(--color-risk-high)' : state.severity === 'MEDIUM' ? 'var(--color-risk-medium)' : 'var(--color-risk-low)',
                      borderColor: state.severity === 'HIGH' ? 'rgba(229,72,77,0.3)' : state.severity === 'MEDIUM' ? 'rgba(245,194,68,0.3)' : 'rgba(52,211,153,0.3)',
                    }}>
                      Score: {state.risk_score}
                    </span>
                  )}
                </motion.div>
              );
            })}
          </div>

          {finalResult && (
            <motion.div
              initial={{ y: 10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              className="mt-6 pt-4 text-center"
              style={{ borderTop: '1px solid var(--color-border)' }}
            >
              <p className="text-sm font-medium mb-2" style={{ color: 'var(--color-accent)' }}>
                ✓ Analysis Complete — Redirecting to results...
              </p>
            </motion.div>
          )}
        </motion.div>
      )}
    </div>
  );
}
