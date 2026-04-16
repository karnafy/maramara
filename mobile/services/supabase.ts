import "react-native-url-polyfill/auto";
import { createClient } from "@supabase/supabase-js";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";
import { SUPABASE_URL, SUPABASE_ANON_KEY } from "../utils/constants";

// Guard every localStorage access so the web build (which runs in Node during
// `expo export`) doesn't crash with `ReferenceError: localStorage is not defined`.
const hasLocalStorage = (): boolean =>
  typeof globalThis !== "undefined" &&
  typeof (globalThis as any).localStorage !== "undefined";

const ExpoSecureStoreAdapter = {
  getItem: (key: string) =>
    Platform.OS === "web"
      ? Promise.resolve(hasLocalStorage() ? (globalThis as any).localStorage.getItem(key) : null)
      : SecureStore.getItemAsync(key),
  setItem: (key: string, value: string) =>
    Platform.OS === "web"
      ? Promise.resolve(hasLocalStorage() ? (globalThis as any).localStorage.setItem(key, value) : undefined)
      : SecureStore.setItemAsync(key, value),
  removeItem: (key: string) =>
    Platform.OS === "web"
      ? Promise.resolve(hasLocalStorage() ? (globalThis as any).localStorage.removeItem(key) : undefined)
      : SecureStore.deleteItemAsync(key),
};

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    storage: ExpoSecureStoreAdapter as any,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false,
  },
});
