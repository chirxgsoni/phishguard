import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import {
  ShieldAlert, ShieldCheck, AlertTriangle, Link2,
  Eye, FileText, Download, Copy, CheckCircle,
  ArrowLeft, Loader2, Globe, Mail, QrCode, Image,
} from 'lucide-react';
import RiskBadge from '../components/RiskBadge';
import { getScan, getReports } from '../api';

const typeIcons = {
  typosquatting: Globe,
  subdomain_spoofing: Link2,
  high_risk_tld: AlertTriangle,
  open_redirect: Link2,
  bare_ip_hostname: Globe,
  idn_homograph: Eye,
  hidden_html_obfuscation: FileText,
  urgency: AlertTriangle,
  fear: ShieldAlert,
  authority: ShieldAlert,
  greed: AlertTriangle,
};

/* ── Demo fallback data ──────────────────────────────── */
const DEMO_RESULT = {
  scan_id: 'demo-scan',
  user_id: 'demo',
  source_type: 'email',
  risk_score: 87,
  severity: 'HIGH',
  status: 'completed',
  recommended_action: 'CRITICAL THREAT: DO NOT CLICK links. Quarantine message immediately, block sender and associated domains.',
  explanation: 'PhishGuard analyzed this message and determined it poses a HIGH risk (Score: 87/100). The primary threat indicators include typosquatting of PayPal (paypa1.com), subdomain brand impersonation (wellsfargo.com appears in subdomain but real domain is update.xyz), and artificial urgency language demanding action within 24 hours.',
  evidence: [
    { id: 'e1', layer: 1, type: 'typosquatting', severity: 'HIGH', human_label: 'Potential typosquatting of PayPal (paypal.com)', raw_match: 'paypa1.com', metadata: { target_brand: 'PayPal', edit_distance: 1 } },
    { id: 'e2', layer: 1, type: 'subdomain_spoofing', severity: 'HIGH', human_label: "Subdomain brand impersonation: 'Wells Fargo' in subdomain, real domain is update.xyz", raw_match: 'wellsfargo.com.update.xyz', metadata: { target_brand: 'Wells Fargo' } },
    { id: 'e3', layer: 1, type: 'high_risk_tld', severity: 'MEDIUM', human_label: 'Suspicious / high-risk Top-Level Domain (.xyz)', raw_match: '.xyz' },
    { id: 'e4', layer: 2, type: 'urgency', severity: 'MEDIUM', human_label: 'Artificial Urgency & Time Pressure', raw_match: 'within 24 hours', span_start: 45, span_end: 60 },
    { id: 'e5', layer: 2, type: 'fear', severity: 'HIGH', human_label: 'Fear, Intimidation & Threat Inducement', raw_match: 'unauthorized access', span_start: 10, span_end: 30 },
  ],
};

export default function ScanResultPage() {
  const { id } = useParams();
  const [scan, setScan] = useState(null);
  const [reports, setReports] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState('');

  useEffect(() => {
    setLoading(true);
    getScan(id)
      .then(data => { setScan(data); setLoading(false); })
      .catch(() => { setScan({ ...DEMO_RESULT, scan_id: id }); setLoading(false); });

    getReports(id)
      .then(setReports)
      .catch(() => setReports(null));
  }, [id]);

  function copyToClipboard(text, label) {
    navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(''), 2000);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 size={32} style={{ color: 'var(--color-accent)' }} className="animate-spin" />
      </div>
    );
  }

  if (!scan) return null;

  const severityColor =
    scan.severity === 'HIGH' ? 'var(--color-risk-high)' :
    scan.severity === 'MEDIUM' ? 'var(--color-risk-medium)' :
    'var(--color-risk-low)';

  const gaugeData = [
    { value: scan.risk_score },
    { value: 100 - scan.risk_score },
  ];

  const sortedEvidence = [...(scan.evidence || [])].sort((a, b) => {
    const sev = { HIGH: 3, MEDIUM: 2, LOW: 1 };
    return (sev[b.severity] || 0) - (sev[a.severity] || 0);
  });

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      {/* ── Back link ─────────────────────────────────── */}
      <Link to="/dashboard" className="inline-flex items-center gap-1.5 text-xs font-mono mb-6 no-underline"
        style={{ color: 'var(--color-text-muted)' }}
      >
        <ArrowLeft size={12} /> Back to Dashboard
      </Link>

      {/* ── Score Header ──────────────────────────────── */}
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="card flex items-center gap-6 mb-6"
        style={{ padding: '1.5rem' }}
      >
        {/* Ring gauge */}
        <div className="flex-shrink-0" style={{ width: 100, height: 100 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={gaugeData}
                innerRadius={32}
                outerRadius={44}
                startAngle={90}
                endAngle={-270}
                dataKey="value"
                strokeWidth={0}
              >
                <Cell fill={severityColor} />
                <Cell fill="rgba(255,255,255,0.06)" />
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="text-center -mt-[68px]">
            <span className="font-mono font-bold text-2xl" style={{ color: severityColor }}>{scan.risk_score}</span>
            <span className="block font-mono text-[10px]" style={{ color: 'var(--color-text-muted)' }}>/100</span>
          </div>
        </div>

        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <RiskBadge score={scan.risk_score} severity={scan.severity} />
          </div>
          <h1 className="text-lg font-bold mb-1" style={{ color: 'var(--color-text-primary)' }}>
            {scan.severity === 'HIGH' ? 'High Risk Threat Detected' :
             scan.severity === 'MEDIUM' ? 'Suspicious Content Flagged' : 'Low Risk Assessment'}
          </h1>
          <p className="text-xs font-mono" style={{ color: 'var(--color-text-muted)' }}>
            Scan ID: {scan.scan_id} · Source: {scan.source_type}
          </p>
        </div>
      </motion.div>

      {/* ── Explanation ───────────────────────────────── */}
      {scan.explanation && (
        <motion.div
          initial={{ y: 15, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="card mb-6"
          style={{ padding: '1.25rem' }}
        >
          <span className="section-label block mb-3">AI Threat Analysis</span>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
            {scan.explanation}
          </p>
        </motion.div>
      )}

      {/* ── Evidence Cards ────────────────────────────── */}
      <span className="section-label block mb-4">
        Why It's Suspicious — {sortedEvidence.length} Evidence{sortedEvidence.length !== 1 ? 's' : ''}
      </span>
      <div className="flex flex-col gap-3 mb-8">
        <AnimatePresence>
          {sortedEvidence.map((ev, i) => {
            const EvIcon = typeIcons[ev.type] || AlertTriangle;
            const evColor =
              ev.severity === 'HIGH' ? 'var(--color-risk-high)' :
              ev.severity === 'MEDIUM' ? 'var(--color-risk-medium)' :
              'var(--color-risk-low)';

            return (
              <motion.div
                key={ev.id || i}
                initial={{ x: -20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: i * 0.08, duration: 0.3 }}
                className="card"
                style={{ padding: '1rem', borderLeftWidth: 3, borderLeftColor: evColor }}
              >
                <div className="flex items-start gap-3">
                  <div
                    className="flex items-center justify-center rounded-lg flex-shrink-0 mt-0.5"
                    style={{ width: 32, height: 32, backgroundColor: `${evColor}15` }}
                  >
                    <EvIcon size={16} style={{ color: evColor }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                        {ev.human_label}
                      </span>
                      <RiskBadge severity={ev.severity} size="sm" showScore={false} />
                    </div>
                    <div
                      className="font-mono text-xs px-2 py-1 rounded inline-block"
                      style={{
                        backgroundColor: 'var(--color-surface-alt)',
                        color: evColor,
                        border: '1px solid var(--color-border)',
                      }}
                    >
                      {ev.raw_match}
                    </div>
                    <div className="flex gap-3 mt-1.5">
                      <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-muted)' }}>
                        Layer {ev.layer} · {ev.type}
                      </span>
                      {ev.span_start !== undefined && ev.span_start !== null && (
                        <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-muted)' }}>
                          chars {ev.span_start}–{ev.span_end}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {/* ── Recommended Action ────────────────────────── */}
      {scan.recommended_action && (
        <motion.div
          initial={{ y: 15, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="card mb-8"
          style={{
            padding: '1.25rem',
            borderColor: severityColor,
            borderWidth: 1,
          }}
        >
          <span className="section-label block mb-2">Recommended Action</span>
          <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text-primary)' }}>
            {scan.recommended_action}
          </p>
        </motion.div>
      )}

      {/* ── SOAR Reports ──────────────────────────────── */}
      {scan.severity === 'HIGH' && reports && (
        <motion.div
          initial={{ y: 15, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <span className="section-label block mb-4">Generated Reports & Containment Artifacts</span>
          {[
            { key: 'cert_report', label: 'CERT / APWG Incident Report', content: reports.cert_report },
            { key: 'dns_sinkhole', label: 'DNS Sinkhole Rule', content: reports.dns_sinkhole },
            { key: 'suricata_rule', label: 'Suricata / Snort IDS Rule', content: reports.suricata_rule },
          ].filter(r => r.content).map(r => (
            <div key={r.key} className="card mb-4" style={{ padding: '1rem' }}>
              <div className="flex items-center justify-between mb-3">
                <span className="font-mono text-xs font-semibold tracking-wider uppercase"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  {r.label}
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => copyToClipboard(r.content, r.key)}
                    className="btn-outline"
                    style={{ padding: '4px 10px', fontSize: '10px' }}
                  >
                    {copied === r.key ? <CheckCircle size={10} /> : <Copy size={10} />}
                    {copied === r.key ? 'Copied' : 'Copy'}
                  </button>
                  <button
                    onClick={() => {
                      const blob = new Blob([r.content], { type: 'text/plain' });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `phishguard_${r.key}_${scan.scan_id.slice(0, 8)}.txt`;
                      a.click();
                    }}
                    className="btn-outline"
                    style={{ padding: '4px 10px', fontSize: '10px' }}
                  >
                    <Download size={10} /> Download
                  </button>
                </div>
              </div>
              <pre
                className="font-mono text-xs leading-relaxed overflow-x-auto p-3 rounded-lg"
                style={{
                  backgroundColor: 'var(--color-bg)',
                  color: 'var(--color-text-secondary)',
                  border: '1px solid var(--color-border)',
                  maxHeight: 300,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {r.content}
              </pre>
            </div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
