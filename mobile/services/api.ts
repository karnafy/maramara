import { API_URL } from "../utils/constants";
import { supabase } from "./supabase";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };
  if (session?.access_token) headers.Authorization = `Bearer ${session.access_token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  const body = await res.json().catch(() => ({}));
  if (!res.ok || body.success === false) {
    throw new Error(body?.error?.message || `HTTP ${res.status}`);
  }
  return body.data as T;
}

export const api = {
  auth: {
    me: () => request<any>("/auth/api/me"),
  },
  voice: {
    startEnrollment: () => request<any>("/voice/enroll/start", { method: "POST" }),
    completeEnrollment: () => request<any>("/voice/enroll/complete", { method: "POST" }),
    retrain: () => request<any>("/voice/retrain", { method: "POST" }),
    uploadChunk: async (audioFile: Blob, index: number) => {
      const fd = new FormData();
      fd.append("audio", audioFile as any);
      fd.append("index", String(index));
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`${API_URL}/voice/enroll/chunk`, {
        method: "POST",
        headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
        body: fd,
      });
      return res.json();
    },
  },
  audio: {
    uploadChunk: async (audioFile: Blob, meta: { duration: number; startedAt: string; endedAt: string }) => {
      const fd = new FormData();
      fd.append("audio", audioFile as any);
      fd.append("duration_sec", String(meta.duration));
      fd.append("started_at", meta.startedAt);
      fd.append("ended_at", meta.endedAt);
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`${API_URL}/api/audio/chunk`, {
        method: "POST",
        headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
        body: fd,
      });
      const body = await res.json();
      if (!body.success) throw new Error(body.error?.message);
      return body.data;
    },
    status: () => request<any>("/api/audio/status"),
  },
  dashboard: {
    today: () => request<any>("/dashboard/api/today"),
    week: () => request<any>("/dashboard/api/week"),
    timeline: (date: string) => request<any>(`/dashboard/api/timeline?date=${date}`),
  },
  insights: {
    weekly: () => request<any>("/api/insights/weekly"),
    terms: (type?: string) => request<any>(`/api/insights/terms${type ? `?type=${type}` : ""}`),
    triggers: () => request<any>("/api/insights/triggers"),
    calming: () => request<any>("/api/insights/calming"),
  },
};
