import { View, Text, ScrollView, StyleSheet } from "react-native";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../services/api";
import { colors, spacing, radii, typography } from "../../utils/theme";

export default function Home() {
  const { t } = useTranslation();
  const { data: today } = useQuery({ queryKey: ["today"], queryFn: api.dashboard.today });

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.greeting}>{t("home.greeting")}</Text>
      <Text style={styles.subtitle}>{t("home.todaySnapshot")}</Text>

      <View style={styles.kpiGrid}>
        <KPI label={t("home.kpi.calming")} value={today?.calming_count} color={colors.positive} />
        <KPI label={t("home.kpi.triggers")} value={today?.negative_count} color={colors.negative} />
        <KPI label={t("home.kpi.intensity")} value={today?.intensity_avg?.toFixed(1)} />
        <KPI label={t("home.kpi.peakHour")} value={today?.peak_frustration_hour} />
      </View>

      <View style={styles.insightCard}>
        <Text style={styles.insightTitle}>{t("home.mainInsight")}</Text>
        <Text style={styles.insightText}>
          {today?.summary_text || t("home.gatheringData")}
        </Text>
      </View>
    </ScrollView>
  );
}

function KPI({ label, value, color = colors.text }: { label: string; value: any; color?: string }) {
  return (
    <View style={styles.kpi}>
      <Text style={styles.kpiLabel}>{label}</Text>
      <Text style={[styles.kpiValue, { color }]}>{value ?? "—"}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.lg },
  greeting: { ...typography.h2, color: colors.text },
  subtitle: { color: colors.textMuted, marginBottom: spacing.lg },
  kpiGrid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.md, marginBottom: spacing.lg },
  kpi: { flex: 1, minWidth: "45%", backgroundColor: colors.surface, padding: spacing.md, borderRadius: radii.md },
  kpiLabel: { fontSize: 12, color: colors.textMuted, marginBottom: 4 },
  kpiValue: { fontSize: 24, fontWeight: "700" },
  insightCard: { backgroundColor: colors.primaryLight, padding: spacing.lg, borderRadius: radii.lg },
  insightTitle: { fontWeight: "700", fontSize: 16, color: colors.primary, marginBottom: spacing.sm },
  insightText: { color: colors.text, lineHeight: 22 },
});
