import { motion } from 'framer-motion';
import {
  AlertTriangle,
  CheckCircle,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';

/**
 * Reusable RiskBadge — shows a colored severity pill with score.
 * Used across Dashboard, Result page, and history table.
 */
export default function RiskBadge({ score, severity, showScore = true, size = 'md' }) {
  const config = {
    LOW:    { bg: 'var(--color-risk-low-bg)',    color: 'var(--color-risk-low)',    border: 'rgba(52,211,153,0.3)',  Icon: ShieldCheck },
    MEDIUM: { bg: 'var(--color-risk-medium-bg)', color: 'var(--color-risk-medium)', border: 'rgba(245,194,68,0.3)', Icon: AlertTriangle },
    HIGH:   { bg: 'var(--color-risk-high-bg)',   color: 'var(--color-risk-high)',   border: 'rgba(229,72,77,0.3)',  Icon: ShieldAlert },
  };
  const c = config[severity] || config.LOW;
  const sizeClass = size === 'sm' ? 'text-[10px] px-2 py-0.5' : 'text-[11px] px-3 py-1';

  return (
    <motion.span
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className="font-mono font-semibold tracking-wider uppercase inline-flex items-center gap-1.5 rounded-full"
      style={{
        backgroundColor: c.bg,
        color: c.color,
        border: `1px solid ${c.border}`,
        fontSize: size === 'sm' ? '10px' : '11px',
        padding: size === 'sm' ? '2px 8px' : '4px 12px',
      }}
    >
      <c.Icon size={size === 'sm' ? 10 : 13} />
      {severity}
      {showScore && score !== undefined && (
        <span style={{ opacity: 0.7 }}>{score}</span>
      )}
    </motion.span>
  );
}
