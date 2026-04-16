import Constants from "expo-constants";

export const API_URL = (Constants.expoConfig?.extra?.apiUrl as string) ||
  process.env.EXPO_PUBLIC_API_URL ||
  "http://localhost:5000";

export const SUPABASE_URL = (Constants.expoConfig?.extra?.supabaseUrl as string) ||
  process.env.EXPO_PUBLIC_SUPABASE_URL ||
  "";

export const SUPABASE_ANON_KEY = (Constants.expoConfig?.extra?.supabaseAnonKey as string) ||
  process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY ||
  "";

export const AUDIO_CHUNK_DURATION_SEC = 10;
export const LISTEN_INTERVAL_MS = 15_000;
export const AUDIO_SAMPLE_RATE = 16_000;
