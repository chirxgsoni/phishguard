import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, Mail, KeyRound } from 'lucide-react';
import { useAuth } from '../auth';
import LoadingSpinner from '../components/LoadingSpinner';

export default function AuthPage() {
  const { signInWithEmail, signUpWithEmail, signInWithGoogle, signInDemo, isAuthenticated, loading: authLoading, authError } = useAuth();
  const navigate = useNavigate();
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // Capture URL errors or context auth errors
  useEffect(() => {
    if (authError) {
      setError(authError);
    }
    const searchParams = new URLSearchParams(window.location.search);
    const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
    const urlErr = searchParams.get('error_description') || searchParams.get('error') ||
                   hashParams.get('error_description') || hashParams.get('error');
    if (urlErr) {
      setError(decodeURIComponent(urlErr.replace(/\+/g, ' ')));
    }
  }, [authError]);

  const isOAuthCallback = window.location.search.includes('code=') || window.location.hash.includes('access_token=');
  if (authLoading && isOAuthCallback) {
    return <LoadingSpinner message="Completing Google sign-in..." />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isSignUp) {
        await signUpWithEmail(email, password);
        sessionStorage.setItem('nexus_pending_email', email);
        navigate(`/verify-otp?email=${encodeURIComponent(email)}`, { state: { email } });
        return;
      } else {
        await signInWithEmail(email, password);
        navigate('/dashboard');
      }
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

        {/* Have OTP link */}
        <div className="text-center -mt-1 mb-2">
          <Link
            to={email ? `/verify-otp?email=${encodeURIComponent(email)}` : '/verify-otp'}
            className="inline-flex items-center gap-1.5 text-xs font-mono no-underline hover:underline transition-colors"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            <KeyRound size={12} style={{ color: 'var(--color-accent)' }} />
            <span>Have a verification code? Verify OTP</span>
          </Link>
        </div>

        {/* Divider */}
        <div className="flex items-center gap-3 my-4">
          <div className="flex-1 h-px" style={{ backgroundColor: 'var(--color-border)' }} />
          <span className="text-xs font-mono" style={{ color: 'var(--color-text-muted)' }}>OR</span>
          <div className="flex-1 h-px" style={{ backgroundColor: 'var(--color-border)' }} />
        </div>

        {/* Google + Demo */}
        <div className="flex flex-col gap-3">
          <button onClick={handleGoogle} className="btn-outline justify-center" style={{ width: '100%' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            Continue with Google
          </button>
          <button onClick={handleDemo} className="btn-outline justify-center" style={{ width: '100%' }}>
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
