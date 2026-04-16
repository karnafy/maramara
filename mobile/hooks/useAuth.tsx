import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { supabase } from "../services/supabase";
import { api } from "../services/api";

type Profile = {
  id: string;
  email: string;
  role: "user" | "therapist" | "admin";
  full_name: string | null;
  language: "he" | "en";
  onboarding_completed: boolean;
};

type AuthCtx = {
  user: any | null;
  profile: Profile | null;
  loading: boolean;
  signIn: (p: { email: string; password: string }) => Promise<void>;
  signUp: (p: { email: string; password: string; full_name: string }) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthCtx | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<any | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setLoading(false);
      if (session?.user) loadProfile();
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_evt, session) => {
      setUser(session?.user ?? null);
      if (session?.user) loadProfile();
      else setProfile(null);
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  const loadProfile = async () => {
    try {
      const me = await api.auth.me();
      setProfile(me);
    } catch {}
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        profile,
        loading,
        signIn: async ({ email, password }) => {
          const { error } = await supabase.auth.signInWithPassword({ email, password });
          if (error) throw error;
        },
        signUp: async ({ email, password, full_name }) => {
          const { error } = await supabase.auth.signUp({
            email,
            password,
            options: { data: { full_name } },
          });
          if (error) throw error;
        },
        signOut: async () => {
          await supabase.auth.signOut();
          setProfile(null);
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
