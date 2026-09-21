import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, Mail, Globe } from 'lucide-react';
import { useAuth } from '../auth';

export default function AuthPage() {
  const { signInWithEmail, signUpWithEmail, signInWithGoogle, signInDemo } = useAuth();
  const navigate = useNavigate();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isSignUp) {
        await signUpWithEmail(email, password);
      } else {
        await signInWithEmail(email, password);
      }
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Authentication failed');
    }
    setLoading(false);
  }

  async function handleGoogle() {
    try {
      await signInWithGoogle();
    } catch (err) {
      setError(err.message || 'Google sign-in failed');
    }
  }

  function handleDemo() {
    signInDemo();
    navigate('/dashboard');
  }

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-56px)] px-4">
      <motion.div
        initial={{ y: 30, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.4 }}
        className="card w-full max-w-sm"
        style={{ padding: '2.5rem 2rem' }}
      >
        {/* Header */}
        <div className="flex flex-col items-center mb-8">
          <div
            className="flex items-center justify-center rounded-xl mb-4"
            style={{
              width: 48, height: 48,
              backgroundColor: 'var(--color-accent-dim)',
            }}
          >
            <Shield size={24} style={{ color: 'var(--color-accent)' }} />
          </div>
          <h1 className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
            {isSignUp ? 'Create Account' : 'Welcome Back'}
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>
            {isSignUp ? 'Start detecting phishing threats' : 'Sign in to your dashboard'}
          </p>
        </div>

        {/* Error */}
        {error && (
          <div
            className="rounded-lg px-3 py-2 text-sm mb-4 font-mono"
            style={{
              backgroundColor: 'var(--color-risk-high-bg)',
              color: 'var(--color-risk-high)',
              border: '1px solid rgba(229,72,77,0.3)',
            }}
          >
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-3 mb-4">
          <input
            type="email"
            placeholder="Email address"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            minLength={6}
          />
          <button type="submit" className="btn-primary justify-center" disabled={loading}
            style={{ width: '100%', padding: '10px' }}
          >
            <Mail size={14} />
            {loading ? 'Loading...' : isSignUp ? 'Sign Up' : 'Sign In'}
          </button>
        </form>

        {/* Divider */}
        <div className="flex items-center gap-3 my-4">
          <div className="flex-1 h-px" style={{ backgroundColor: 'var(--color-border)' }} />
          <span className="text-xs font-mono" style={{ color: 'var(--color-text-muted)' }}>OR</span>
          <div className="flex-1 h-px" style={{ backgroundColor: 'var(--color-border)' }} />
        </div>

        {/* Google + Demo */}
        <div className="flex flex-col gap-2">
          <button onClick={handleGoogle} className="btn-outline justify-center" style={{ width: '100%' }}>
            <Globe size={14} />
            Continue with Google
          </button>
          <button onClick={handleDemo} className="btn-outline justify-center" style={{ width: '100%', color: 'var(--color-accent)' }}>
            <Shield size={14} />
            Demo Mode (No Login)
          </button>
        </div>

        {/* Toggle */}
        <p className="text-center text-sm mt-6" style={{ color: 'var(--color-text-secondary)' }}>
          {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            onClick={() => { setIsSignUp(!isSignUp); setError(''); }}
            className="font-semibold bg-transparent border-none cursor-pointer"
            style={{ color: 'var(--color-accent)' }}
          >
            {isSignUp ? 'Sign In' : 'Sign Up'}
          </button>
        </p>
      </motion.div>
    </div>
  );
}
