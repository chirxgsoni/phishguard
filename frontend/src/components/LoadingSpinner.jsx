import { motion } from 'framer-motion';
import { Shield } from 'lucide-react';

/**
 * Full-page loading spinner with PhishGuard branding.
 * Used during auth state resolution and lazy-loaded routes.
 */
export default function LoadingSpinner({ message = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        className="flex items-center justify-center rounded-xl"
        style={{
          width: 48, height: 48,
          backgroundColor: 'var(--color-accent-dim)',
        }}
      >
        <Shield size={22} style={{ color: 'var(--color-accent)' }} />
      </motion.div>
      <span className="font-mono text-xs tracking-wider" style={{ color: 'var(--color-text-muted)' }}>
        {message}
      </span>
    </div>
  );
}
