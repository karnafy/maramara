export const colors = {
  primary: "#4F46E5",
  primaryLight: "#eef2ff",
  positive: "#10b981",
  negative: "#ef4444",
  neutral: "#64748b",
  danger: "#dc2626",
  bg: "#fafafa",
  surface: "#ffffff",
  border: "#e2e8f0",
  text: "#0f172a",
  textMuted: "#64748b",
};

export const spacing = { xs: 4, sm: 8, md: 12, lg: 20, xl: 32 };
export const radii = { sm: 6, md: 10, lg: 16, xl: 24, full: 9999 };
export const typography = {
  h1: { fontSize: 32, fontWeight: "700" as const, color: colors.text },
  h2: { fontSize: 24, fontWeight: "700" as const, color: colors.text },
  h3: { fontSize: 18, fontWeight: "600" as const, color: colors.text },
  body: { fontSize: 16, color: colors.text },
};
