import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, Session } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';

interface AuthContextType {
  user: User | null;
  session: Session | null;
  loading: boolean;
  signIn: (email: string, pass: string) => Promise<{ error: any }>;
  signOut: () => Promise<void>;
  getToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;

    // Guaranteed resolution timer to prevent infinite loading state
    const timer = setTimeout(() => {
      if (isMounted) {
        setLoading(false);
      }
    }, 2000);

    // 1. Listen for auth changes (fires INITIAL_SESSION in Supabase v2)
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, currentSession) => {
      if (isMounted) {
        setSession(currentSession);
        setUser(currentSession?.user ?? null);
        setLoading(false);
        clearTimeout(timer);
      }
    });

    // 2. Fetch initial session explicitly as fallback
    supabase.auth.getSession().then(({ data: { session: currentSession } }) => {
      if (isMounted) {
        setSession(currentSession);
        setUser(currentSession?.user ?? null);
        setLoading(false);
        clearTimeout(timer);
      }
    }).catch(() => {
      if (isMounted) {
        setLoading(false);
        clearTimeout(timer);
      }
    });

    return () => {
      isMounted = false;
      clearTimeout(timer);
      subscription.unsubscribe();
    };
  }, []);

  const signIn = async (email: string, pass: string) => {
    const res = await supabase.auth.signInWithPassword({
      email,
      password: pass
    });
    if (res.data?.session) {
      setSession(res.data.session);
      setUser(res.data.session.user ?? null);
    }
    return res;
  };

  const signOut = async () => {
    await supabase.auth.signOut();
    setSession(null);
    setUser(null);
  };

  const getToken = async (): Promise<string | null> => {
    const { data: { session: currentSession } } = await supabase.auth.getSession();
    return currentSession?.access_token || session?.access_token || null;
  };

  return (
    <AuthContext.Provider value={{ user, session, loading, signIn, signOut, getToken }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
