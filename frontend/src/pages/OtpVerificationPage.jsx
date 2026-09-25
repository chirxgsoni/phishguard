import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ShieldCheck, Mail, ArrowLeft, RefreshCw, KeyRound, AlertCircle, CheckCircle2, Edit2, Sparkles } from 'lucide-react';
import { useAuth } from '../auth';

const OTP_LENGTH = 6;
const RESEND_COOLDOWN_SECONDS = 60;

export default function OtpVerificationPage() {
  const { verifyOtp, resendOtp, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Retrieve email from URL search params, router state, or sessionStorage
  const searchParams = new URLSearchParams(location.search);
  const initialEmail = searchParams.get('email') ||
                       location.state?.email ||
                       sessionStorage.getItem('nexus_pending_email') ||
                       '';

  const [email, setEmail] = useState(initialEmail);
  const [isEditingEmail, setIsEditingEmail] = useState(!initialEmail);
  const [tempEmail, setTempEmail] = useState(initialEmail);

  const [otp, setOtp] = useState(new Array(OTP_LENGTH).fill(''));
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(RESEND_COOLDOWN_SECONDS);

  const inputRefs = useRef([]);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // Cooldown timer for resend
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const interval = setInterval(() => {
      setResendCooldown(prev => prev - 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [resendCooldown]);

  // Focus the first input box on load if email is set
  useEffect(() => {
    if (email && inputRefs.current[0]) {
      inputRefs.current[0].focus();
    }
  }, [email]);

  // Handle single digit input
  function handleChange(index, e) {
    const val = e.target.value;
    setError('');
    setSuccessMsg('');

    // If backspaced or cleared
    if (!val) {
      const updatedOtp = [...otp];
      updatedOtp[index] = '';
      setOtp(updatedOtp);
      return;
    }

    // Only allow numeric input
    const cleanDigits = val.replace(/\D/g, '');
    if (!cleanDigits) return;

    // Handle multiple digits (e.g. mobile autocomplete or swift typing)
    if (cleanDigits.length > 1) {
      handlePastedCode(cleanDigits);
      return;
    }

    const updatedOtp = [...otp];
    updatedOtp[index] = cleanDigits[0];
    setOtp(updatedOtp);

    // Focus next box if available
    if (index < OTP_LENGTH - 1) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto submit if last digit entered and all are filled
    const fullCode = updatedOtp.join('');
    if (fullCode.length === OTP_LENGTH && updatedOtp.every(d => d !== '')) {
      handleVerify(fullCode);
    }
  }

  // Key navigation (backspace, arrows)
  function handleKeyDown(index, e) {
    if (e.key === 'Backspace') {
      if (!otp[index] && index > 0) {
        inputRefs.current[index - 1]?.focus();
        const updatedOtp = [...otp];
        updatedOtp[index - 1] = '';
        setOtp(updatedOtp);
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowRight' && index < OTP_LENGTH - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  }

  // Paste support
  function handlePaste(e) {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text');
    const digits = pasted.replace(/\D/g, '').slice(0, OTP_LENGTH);
    if (!digits) return;
    handlePastedCode(digits);
  }

  function handlePastedCode(digits) {
    const updatedOtp = new Array(OTP_LENGTH).fill('');
    for (let i = 0; i < digits.length; i++) {
      updatedOtp[i] = digits[i];
    }
    setOtp(updatedOtp);

    const nextIndex = Math.min(digits.length, OTP_LENGTH - 1);
    inputRefs.current[nextIndex]?.focus();

    if (digits.length === OTP_LENGTH) {
      handleVerify(digits);
    }
  }

  // Verify OTP submission
  async function handleVerify(codeToVerify) {
    const token = codeToVerify || otp.join('');
    if (token.length !== OTP_LENGTH) {
      setError(`Please enter the full ${OTP_LENGTH}-digit verification code.`);
      return;
    }

    if (!email) {
      setError('Please provide the email address you signed up with.');
      setIsEditingEmail(true);
      return;
    }

    setError('');
    setLoading(true);

    try {
      await verifyOtp(email.trim(), token, 'signup');
      setSuccessMsg('Email verified successfully! Redirecting...');
      sessionStorage.removeItem('nexus_pending_email');
      setTimeout(() => {
        navigate('/dashboard', { replace: true });
      }, 700);
    } catch (err) {
      console.error('OTP verification error:', err);
      const msg = err.message?.toLowerCase().includes('expired')
        ? 'Verification code has expired. Please click resend to get a new code.'
        : err.message || 'Invalid verification code. Please check and try again.';
      setError(msg);
      setLoading(false);
    }
  }

  // Resend OTP
  async function handleResend() {
    if (!email) {
      setError('Email address is missing.');
      setIsEditingEmail(true);
      return;
    }

    setError('');
    setSuccessMsg('');
    setResending(true);

    try {
      await resendOtp(email.trim(), 'signup');
      setSuccessMsg('A new verification code has been dispatched to your email.');
      setResendCooldown(RESEND_COOLDOWN_SECONDS);
      // Clear current boxes and focus first
      setOtp(new Array(OTP_LENGTH).fill(''));
      inputRefs.current[0]?.focus();
    } catch (err) {
      console.error('Resend OTP error:', err);
      setError(err.message || 'Failed to resend verification code. Please try again.');
    } finally {
      setResending(false);
    }
  }

  // Update recipient email
  function handleSaveEmail(e) {
    e.preventDefault();
    if (!tempEmail || !tempEmail.includes('@')) {
      setError('Please enter a valid email address.');
      return;
    }
    setEmail(tempEmail);
    sessionStorage.setItem('nexus_pending_email', tempEmail);
    setIsEditingEmail(false);
    setError('');
    setOtp(new Array(OTP_LENGTH).fill(''));
    // Trigger a fresh code to the new address
    resendOtp(tempEmail.trim(), 'signup')
      .then(() => {
        setSuccessMsg(`Code sent to ${tempEmail}`);
        setResendCooldown(RESEND_COOLDOWN_SECONDS);
      })
      .catch((err) => {
        console.warn('Auto-resend to updated email notice:', err);
      });
  }

  // Demo auto-fill helper for convenience
  function handleDemoFill() {
    handlePastedCode('123456');
  }

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-56px)] px-4 py-8">
      <motion.div
        initial={{ y: 25, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.35 }}
        className="card w-full max-w-md relative overflow-hidden"
        style={{ padding: '2.5rem 2rem' }}
      >
        {/* Subtle accent glow top border */}
        <div
          className="absolute top-0 left-0 right-0 h-1"
          style={{
            background: 'linear-gradient(90deg, transparent, var(--color-accent), transparent)',
          }}
        />

        {/* Back Link */}
        <div className="mb-6">
          <Link
            to="/auth"
            className="inline-flex items-center gap-1.5 text-xs font-mono no-underline transition-colors hover:text-white"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            <ArrowLeft size={13} />
            Back to Sign In
          </Link>
        </div>

        {/* Icon & Title */}
        <div className="flex flex-col items-center text-center mb-6">
          <div
            className="flex items-center justify-center rounded-2xl mb-4 relative"
            style={{
              width: 54,
              height: 54,
              backgroundColor: 'var(--color-accent-dim)',
              boxShadow: '0 0 24px rgba(200, 255, 51, 0.18)',
            }}
          >
            <KeyRound size={26} style={{ color: 'var(--color-accent)' }} />
          </div>

          <h1 className="text-xl font-bold tracking-tight" style={{ color: 'var(--color-text-primary)' }}>
            Enter Verification Code
          </h1>
          <p className="text-xs sm:text-sm mt-1.5 max-w-xs" style={{ color: 'var(--color-text-secondary)' }}>
            We've sent a 6-digit confirmation code to your email address to complete your registration.
          </p>
        </div>

        {/* Target Email Banner or Edit Box */}
        <div className="mb-6">
          {!isEditingEmail && email ? (
            <div
              className="flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs"
              style={{
                backgroundColor: 'var(--color-surface-alt)',
                border: '1px solid var(--color-border)',
              }}
            >
              <div className="flex items-center gap-2 overflow-hidden">
                <Mail size={14} style={{ color: 'var(--color-accent)', flexShrink: 0 }} />
                <span className="font-mono truncate" style={{ color: 'var(--color-text-primary)' }}>
                  {email}
                </span>
              </div>
              <button
                type="button"
                onClick={() => {
                  setTempEmail(email);
                  setIsEditingEmail(true);
                }}
                className="flex items-center gap-1 font-mono text-[11px] bg-transparent border-none cursor-pointer hover:underline transition-colors"
                style={{ color: 'var(--color-accent)', flexShrink: 0 }}
                title="Change email"
              >
                <Edit2 size={11} />
                Change
              </button>
            </div>
          ) : (
            <form onSubmit={handleSaveEmail} className="flex gap-2">
              <input
                type="email"
                placeholder="Enter your email"
                value={tempEmail}
                onChange={e => setTempEmail(e.target.value)}
                className="text-xs font-mono py-2"
                required
                autoFocus
              />
              <button
                type="submit"
                className="btn-primary text-xs whitespace-nowrap"
                style={{ padding: '0 12px' }}
              >
                Send Code
              </button>
            </form>
          )}
        </div>

        {/* Success Alert */}
        {successMsg && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-xs mb-4 font-mono"
            style={{
              backgroundColor: 'var(--color-risk-low-bg)',
              color: 'var(--color-risk-low)',
              border: '1px solid rgba(52, 211, 153, 0.3)',
            }}
          >
            <CheckCircle2 size={14} className="shrink-0" />
            <span>{successMsg}</span>
          </motion.div>
        )}

        {/* Error Alert */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-xs mb-4 font-mono"
            style={{
              backgroundColor: 'var(--color-risk-high-bg)',
              color: 'var(--color-risk-high)',
              border: '1px solid rgba(229, 72, 77, 0.3)',
            }}
          >
            <AlertCircle size={14} className="shrink-0" />
            <span className="flex-1">{error}</span>
          </motion.div>
        )}

        {/* 6 Digit Input Boxes */}
        <div className="flex justify-between gap-2 sm:gap-2.5 mb-6" onPaste={handlePaste}>
          {otp.map((digit, idx) => {
            const isFilled = digit !== '';
            return (
              <input
                key={idx}
                ref={el => (inputRefs.current[idx] = el)}
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]*"
                maxLength={1}
                value={digit}
                onChange={e => handleChange(idx, e)}
                onKeyDown={e => handleKeyDown(idx, e)}
                disabled={loading}
                className="w-11 sm:w-12 h-14 sm:h-16 text-center text-xl sm:text-2xl font-mono font-bold rounded-xl transition-all duration-150"
                style={{
                  backgroundColor: 'var(--color-surface-alt)',
                  border: isFilled
                    ? '1.5px solid var(--color-accent)'
                    : '1px solid var(--color-border)',
                  boxShadow: isFilled ? '0 0 10px rgba(200, 255, 51, 0.15)' : 'none',
                  color: 'var(--color-text-primary)',
                  caretColor: 'var(--color-accent)',
                }}
              />
            );
          })}
        </div>

        {/* Action Button */}
        <button
          type="button"
          onClick={() => handleVerify()}
          disabled={loading || otp.some(d => d === '')}
          className="btn-primary justify-center w-full mb-4 text-sm"
          style={{ padding: '12px' }}
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <RefreshCw size={14} className="animate-spin" />
              Verifying Code...
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <ShieldCheck size={16} />
              Verify & Complete Sign Up
            </span>
          )}
        </button>

        {/* Resend Cooldown Section */}
        <div className="flex flex-col items-center gap-2 text-center text-xs mt-2">
          {resendCooldown > 0 ? (
            <p className="font-mono text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Resend verification code in{' '}
              <span className="font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                {resendCooldown}s
              </span>
            </p>
          ) : (
            <button
              type="button"
              onClick={handleResend}
              disabled={resending || loading}
              className="flex items-center gap-1.5 font-mono text-xs bg-transparent border-none cursor-pointer transition-colors"
              style={{ color: 'var(--color-accent)' }}
            >
              <RefreshCw size={12} className={resending ? 'animate-spin' : ''} />
              {resending ? 'Sending new code...' : "Didn't receive code? Resend"}
            </button>
          )}

          <p className="text-[11px] mt-1" style={{ color: 'var(--color-text-muted)' }}>
            Code expires in 10 minutes. Remember to inspect your spam or junk folder.
          </p>
        </div>

        {/* Quick Demo Helper */}
        <div
          className="mt-6 pt-4 border-t flex items-center justify-between text-[11px]"
          style={{ borderColor: 'var(--color-border)' }}
        >
          <span className="font-mono" style={{ color: 'var(--color-text-muted)' }}>
            Demo / testing environment?
          </span>
          <button
            type="button"
            onClick={handleDemoFill}
            className="flex items-center gap-1 font-mono text-[11px] bg-transparent border-none cursor-pointer hover:underline"
            style={{ color: 'var(--color-accent)' }}
          >
            <Sparkles size={11} />
            Fill Demo OTP (123456)
          </button>
        </div>
      </motion.div>
    </div>
  );
}
