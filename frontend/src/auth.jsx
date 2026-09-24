import { createContext, useContext, useEffect, useState } from 'react';
import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://placeholder.supabase.co';
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || 'placeholder-anon-key';

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing session
    supabase.auth.getSession().then(({ data: { session: s } = {} }) => {
      setSession(s || null);
      setUser(s?.user ?? null);
      if (s?.access_token) {
        localStorage.setItem('nexus_session', JSON.stringify(s));
      }
      setLoading(false);
    }).catch((err) => {
      console.warn('Supabase getSession failed, checking local storage:', err);
      const raw = localStorage.getItem('nexus_session');
      if (raw) {
        try {
          const s = JSON.parse(raw);
          setSession(s);
          setUser(s?.user ?? null);
        } catch {}
      }
      setLoading(false);
    });

    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s);
      setUser(s?.user ?? null);
      if (s?.access_token) {
        localStorage.setItem('nexus_session', JSON.stringify(s));
      } else {
        localStorage.removeItem('nexus_session');
      }
    });

    return () => subscription.unsubscribe();
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
      options: { redirectTo: window.location.origin + '/dashboard' },
    });
    if (error) throw error;
    return data;
  }

  async function signOut() {
    await supabase.auth.signOut();
    localStorage.removeItem('nexus_session');
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
