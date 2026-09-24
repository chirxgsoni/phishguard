import { createContext, useContext, useEffect, useState } from 'react';
import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://placeholder.supabase.co';
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || 'placeholder-anon-key';

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
    flowType: 'pkce',
  },
});

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function initAuth() {
      try {
        // 1. Check if OAuth error was returned in URL search or hash
        const searchParams = new URLSearchParams(window.location.search);
        const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
        const errParam = searchParams.get('error_description') || searchParams.get('error') ||
                         hashParams.get('error_description') || hashParams.get('error');
        if (errParam) {
          const decoded = decodeURIComponent(errParam.replace(/\+/g, ' '));
          console.error('OAuth error from redirect:', decoded);
          if (mounted) {
            setAuthError(decoded);
            setLoading(false);
          }
          return;
        }

        // 2. Explicitly handle PKCE code exchange if present in URL
        const code = searchParams.get('code');
        if (code) {
          try {
            const { data, error } = await supabase.auth.exchangeCodeForSession(code);
            if (error) {
              console.error('exchangeCodeForSession error:', error);
              if (mounted) setAuthError(error.message);
            } else if (data?.session && mounted) {
              setSession(data.session);
              setUser(data.session.user);
              localStorage.setItem('nexus_session', JSON.stringify(data.session));
              // Clean code from URL to prevent replay errors
              const cleanUrl = new URL(window.location.href);
              cleanUrl.searchParams.delete('code');
              window.history.replaceState({}, document.title, cleanUrl.pathname + cleanUrl.search);
              setLoading(false);
              return;
            }
          } catch (e) {
            console.error('Code exchange exception:', e);
            if (mounted) setAuthError(e.message);
          }
        }

        // 3. Handle hash tokens (implicit flow fallback) if present
        const accessToken = hashParams.get('access_token');
        const refreshToken = hashParams.get('refresh_token');
        if (accessToken && refreshToken) {
          try {
            const { data, error } = await supabase.auth.setSession({
              access_token: accessToken,
              refresh_token: refreshToken,
            });
            if (error) {
              console.error('setSession from hash error:', error);
              if (mounted) setAuthError(error.message);
            } else if (data?.session && mounted) {
              setSession(data.session);
              setUser(data.session.user);
              localStorage.setItem('nexus_session', JSON.stringify(data.session));
              window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
              setLoading(false);
              return;
            }
          } catch (e) {
            console.error('Hash token exception:', e);
            if (mounted) setAuthError(e.message);
          }
        }

        // 4. Retrieve current active session from Supabase
        const { data: { session: s } = {}, error: sessError } = await supabase.auth.getSession();
        if (sessError) {
          console.warn('supabase.auth.getSession error:', sessError);
        }
        if (s?.user && mounted) {
          setSession(s);
          setUser(s.user);
          localStorage.setItem('nexus_session', JSON.stringify(s));
        } else if (mounted) {
          // Check local storage fallback
          const raw = localStorage.getItem('nexus_session');
          if (raw) {
            try {
              const cached = JSON.parse(raw);
              if (cached?.user) {
                setSession(cached);
                setUser(cached.user);
              }
            } catch {}
          }
        }
      } catch (err) {
        console.error('Auth initialization error:', err);
      } finally {
        if (mounted) setLoading(false);
      }
    }

    initAuth();

    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, s) => {
      if (!mounted) return;
      if (s?.user) {
        setSession(s);
        setUser(s.user);
        if (s.access_token) {
          localStorage.setItem('nexus_session', JSON.stringify(s));
        }
        setLoading(false);
      } else if (event === 'SIGNED_OUT') {
        setSession(null);
        setUser(null);
        localStorage.removeItem('nexus_session');
        setLoading(false);
      }
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  async function signInWithEmail(email, password) {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
    return data;
  }

  async function signUpWithEmail(email, password) {
    const { data, error } = await supabase.auth.signUp({ email, password });
    if (error) throw error;
    return data;
  }

  async function signInWithGoogle() {
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/dashboard`,
      },
    });
    if (error) throw error;
    return data;
  }

  async function signOut() {
    await supabase.auth.signOut();
    localStorage.removeItem('nexus_session');
    setSession(null);
    setUser(null);
  }

  // For demo/dev mode when Supabase is not configured
  function signInDemo() {
    const demoSession = {
      access_token: 'demo-token',
      user: {
        id: '00000000-0000-0000-0000-000000000000',
        email: 'demo@nexus.security',
        user_metadata: { name: 'Demo Analyst' },
      },
    };
    setSession(demoSession);
    setUser(demoSession.user);
    localStorage.setItem('nexus_session', JSON.stringify(demoSession));
  }

  const value = {
    session,
    user,
    loading,
    authError,
    signInWithEmail,
    signUpWithEmail,
    signInWithGoogle,
    signInDemo,
    signOut,
    isAuthenticated: !!user,
    isDemo: session?.access_token === 'demo-token',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
