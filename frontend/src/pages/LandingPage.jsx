import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, ScanSearch, FileText, Zap, ArrowRight } from 'lucide-react';

const steps = [
  { Icon: ScanSearch, title: 'Paste or Upload', desc: 'Submit a suspicious email, URL, screenshot, or QR code.' },
  { Icon: Zap,        title: 'Layered Analysis', desc: '5-layer deterministic + AI engine analyzes every indicator.' },
  { Icon: FileText,   title: 'Evidence & Action', desc: 'See exactly why it\'s risky with traceable evidence cards.' },
];

export default function LandingPage() {
  return (
    <div className="flex flex-col items-center min-h-[calc(100vh-56px)]">
      {/* ─── Hero ───────────────────────────────────── */}
      <section className="flex flex-col items-center text-center pt-24 pb-20 px-6 max-w-3xl mx-auto">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.6 }}
          className="flex items-center justify-center rounded-2xl mb-8"
          style={{
            width: 72, height: 72,
            backgroundColor: 'var(--color-accent-dim)',
          }}
        >
          <Shield size={36} style={{ color: 'var(--color-accent)' }} />
        </motion.div>

        <motion.h1
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.15, duration: 0.5 }}
          className="text-5xl font-bold tracking-tight leading-tight mb-4"
          style={{ color: 'var(--color-text-primary)' }}
        >
          Detect. Explain.{' '}
          <span style={{ color: 'var(--color-accent)' }}>Protect.</span>
        </motion.h1>

        <motion.p
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          className="text-lg leading-relaxed max-w-xl mb-10"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          PhishGuard is an explainable phishing threat detection platform. Every risk score is traceable to
          concrete, rule-based evidence — not just "the AI said so."
        </motion.p>

        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.45, duration: 0.5 }}
          className="flex gap-4"
        >
          <Link to="/auth" className="btn-primary no-underline" style={{ padding: '12px 28px', fontSize: '14px' }}>
            Get Started <ArrowRight size={16} />
          </Link>
          <a href="#how-it-works" className="btn-outline no-underline" style={{ padding: '12px 28px', fontSize: '14px' }}>
            How It Works
          </a>
        </motion.div>
      </section>

      {/* ─── How it works ───────────────────────────── */}
      <section id="how-it-works" className="w-full max-w-4xl mx-auto px-6 pb-24">
        <h2 className="section-label text-center mb-12">How It Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {steps.map((step, i) => (
            <motion.div
              key={step.title}
              initial={{ y: 30, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 + i * 0.15, duration: 0.5 }}
              className="card card-hover flex flex-col items-center text-center"
              style={{ padding: '2rem 1.5rem' }}
            >
              <div
                className="flex items-center justify-center rounded-xl mb-5"
                style={{
                  width: 48, height: 48,
                  backgroundColor: 'var(--color-accent-dim)',
                }}
              >
                <step.Icon size={22} style={{ color: 'var(--color-accent)' }} />
              </div>
              <span className="font-mono font-semibold text-xs tracking-wider uppercase mb-1"
                style={{ color: 'var(--color-accent)' }}
              >
                Step {i + 1}
              </span>
              <h3 className="text-base font-semibold mb-2" style={{ color: 'var(--color-text-primary)' }}>
                {step.title}
              </h3>
              <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
                {step.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ─── Footer ─────────────────────────────────── */}
      <footer
        className="w-full text-center py-6 mt-auto font-mono text-xs"
        style={{
          color: 'var(--color-text-muted)',
          borderTop: '1px solid var(--color-border)',
        }}
      >
        PhishGuard — Explainable & Autonomous Phishing Threat Detection Platform
      </footer>
    </div>
  );
}
