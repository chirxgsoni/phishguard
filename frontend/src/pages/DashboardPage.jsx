import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import {
  ScanSearch, ShieldAlert, TrendingUp, Link2,
  Mail, Globe, QrCode, Image, ArrowRight, Plus,
  BarChart3,
} from 'lucide-react';
import RiskBadge from '../components/RiskBadge';
import { listScans, listConnections } from '../api';

/* ── Demo data used when backend not connected ───────────── */
const DEMO_SCANS = [
  { id: 'd1', source_type: 'email', risk_score: 87, severity: 'HIGH', status: 'completed', raw_input_ref: 'URGENT: Unauthorized login detected from paypa1.com...', created_at: new Date(Date.now() - 3600000).toISOString() },
  { id: 'd2', source_type: 'url', risk_score: 42, severity: 'MEDIUM', status: 'completed', raw_input_ref: 'https://secure-login.update.xyz/auth?next=...', created_at: new Date(Date.now() - 7200000).toISOString() },
  { id: 'd3', source_type: 'email', risk_score: 12, severity: 'LOW', status: 'completed', raw_input_ref: 'Your weekly engineering update from ACME Corp', created_at: new Date(Date.now() - 86400000).toISOString() },
  { id: 'd4', source_type: 'qr', risk_score: 78, severity: 'HIGH', status: 'completed', raw_input_ref: 'QR Code Scan → paypa1-secure.xyz', created_at: new Date(Date.now() - 172800000).toISOString() },
  { id: 'd5', source_type: 'email', risk_score: 8, severity: 'LOW', status: 'completed', raw_input_ref: 'Meeting reminder for Sprint 42 retrospective', created_at: new Date(Date.now() - 259200000).toISOString() },
];
const DEMO_TREND = Array.from({ length: 14 }, (_, i) => ({
  day: `${14 - i}d ago`,
  score: Math.floor(Math.random() * 60 + 10),
  scans: Math.floor(Math.random() * 5 + 1),
}));

const sourceIcons = { email: Mail, url: Globe, qr: QrCode, screenshot: Image };

export default function DashboardPage() {
  const [scans, setScans] = useState([]);
  const [connections, setConnections] = useState([]);
  const [trendData] = useState(DEMO_TREND);

  useEffect(() => {
    listScans(1, 10)
      .then(data => setScans(data.items?.length ? data.items : DEMO_SCANS))
      .catch(() => setScans(DEMO_SCANS));
    listConnections()
      .then(data => setConnections(data || []))
      .catch(() => setConnections([]));
  }, []);

  const highRisk = scans.filter(s => s.severity === 'HIGH').length;
  const avgScore = scans.length
    ? Math.round(scans.reduce((a, s) => a + s.risk_score, 0) / scans.length)
    : 0;

  const stats = [
    { label: 'Total Scans', value: scans.length, Icon: ScanSearch, accent: false },
    { label: 'High Risk', value: highRisk, Icon: ShieldAlert, accent: highRisk > 0 },
    { label: 'Avg Score', value: avgScore, Icon: TrendingUp, accent: false },
    { label: 'Connections', value: connections.length, Icon: Link2, accent: false },
  ];

  function formatTime(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    const now = new Date();
    const diff = Math.floor((now - d) / 60000);
    if (diff < 1) return 'just now';
    if (diff < 60) return `${diff}m ago`;
    if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
    return `${Math.floor(diff / 1440)}d ago`;
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* ── Header ─────────────────────────────────────── */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>Dashboard</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>Threat detection overview</p>
      </div>

      {/* ── Stat Cards ─────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {stats.map((s, i) => (
          <motion.div
            key={s.label}
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: i * 0.08, duration: 0.35 }}
            className="card"
          >
            <div className="flex items-center gap-2 mb-3">
              <s.Icon size={14} style={{ color: s.accent ? 'var(--color-risk-high)' : 'var(--color-text-muted)' }} />
              <span className="section-label">{s.label}</span>
            </div>
            <span
              className="text-3xl font-bold font-mono"
              style={{ color: s.accent ? 'var(--color-risk-high)' : 'var(--color-accent)' }}
            >
              {s.value}
            </span>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ── Recent Scans ─────────────────────────────── */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <span className="section-label">Recent Scans</span>
          </div>
          <div className="flex flex-col gap-2">
            {scans.length === 0 ? (
              <div className="card flex flex-col items-center py-12 text-center">
                <ScanSearch size={36} style={{ color: 'var(--color-text-muted)', marginBottom: 12 }} />
                <p className="text-sm font-medium mb-1" style={{ color: 'var(--color-text-secondary)' }}>No scans yet</p>
                <p className="text-xs mb-4" style={{ color: 'var(--color-text-muted)' }}>Submit a suspicious email or URL to get started</p>
                <Link to="/scan/new" className="btn-primary no-underline" style={{ fontSize: '11px' }}>
                  <Plus size={12} /> New Scan
                </Link>
              </div>
            ) : (
              scans.map((scan, i) => {
                const SrcIcon = sourceIcons[scan.source_type] || Mail;
                return (
                  <motion.div
                    key={scan.id}
                    initial={{ x: -15, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ delay: i * 0.05, duration: 0.3 }}
                  >
                    <Link
                      to={`/scan/${scan.id}`}
                      className="card card-hover flex items-center gap-4 no-underline"
                      style={{ padding: '0.75rem 1rem' }}
                    >
                      <div
                        className="flex items-center justify-center rounded-lg flex-shrink-0"
                        style={{
                          width: 36, height: 36,
                          backgroundColor: 'var(--color-surface-alt)',
                          border: '1px solid var(--color-border)',
                        }}
                      >
                        <SrcIcon size={16} style={{ color: 'var(--color-text-secondary)' }} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>
                          {scan.raw_input_ref || 'Scan content'}
                        </p>
                        <p className="text-xs font-mono" style={{ color: 'var(--color-text-muted)' }}>
                          {formatTime(scan.created_at)}
                        </p>
                      </div>
                      <RiskBadge score={scan.risk_score} severity={scan.severity} size="sm" />
                      <ArrowRight size={14} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
                    </Link>
                  </motion.div>
                );
              })
            )}
          </div>
        </div>

        {/* ── Risk Trend Chart ─────────────────────────── */}
        <div>
          <span className="section-label block mb-4">Risk Trend (14 Days)</span>
          <div className="card" style={{ padding: '1rem' }}>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={trendData}>
                <XAxis
                  dataKey="day"
                  tick={{ fontSize: 10, fill: '#6A6A6A', fontFamily: 'var(--font-mono)' }}
                  axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                  tickLine={false}
                  interval={2}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: '#6A6A6A', fontFamily: 'var(--font-mono)' }}
                  axisLine={false}
                  tickLine={false}
                  domain={[0, 100]}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#161616',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 8,
                    fontFamily: 'var(--font-mono)',
                    fontSize: 11,
                  }}
                  labelStyle={{ color: '#9A9A9A' }}
                />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#C8FF33"
                  strokeWidth={2}
                  dot={{ r: 3, fill: '#C8FF33', strokeWidth: 0 }}
                  activeDot={{ r: 5, fill: '#D4FF3D' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
