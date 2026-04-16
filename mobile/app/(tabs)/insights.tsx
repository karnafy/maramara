import { View, Text, ScrollView, StyleSheet } from "react-native";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../services/api";
import { colors, spacing, radii, typography } from "../../utils/theme";

export default function Insights() {
  const { t } = useTranslation();
  const { data } = useQuery({ queryKey: ["weekly"], queryFn: api.insights.weekly });
  const ci = data?.crewai_insights || {};

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={typography.h2}>{t("insights.title")}</Text>
      <Text style={styles.subtitle}>{t("insights.subtitle")}</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>{t("insights.reflection")}</Text>
        <Text style={styles.cardBody}>{ci.user_reflection || t("insights.waiting")}</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>{t("insights.topTriggers")}</Text>
        {(ci.triggers || []).slice(0, 5).map((tr: any, i: number) => (
          <Text key={i} style={styles.listItem}>• {tr.topic} ({tr.frequency}×)</Text>
        ))}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>{t("insights.topRegulation")}</Text>
        {(ci.regulations || []).slice(0, 5).map((r: any, i: number) => (
          <Text key={i} style={styles.listItem}>• {r.source} ({r.frequency}×)</Text>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.lg },
  subtitle: { color: colors.textMuted, marginBottom: spacing.lg },
  card: { backgroundColor: colors.surface, padding: spacing.lg, borderRadius: radii.lg, marginBottom: spacing.md },
  cardTitle: { fontWeight: "700", fontSize: 16, marginBottom: spacing.sm, color: colors.primary },
  cardBody: { color: colors.text, lineHeight: 22 },
  listItem: { color: colors.text, marginBottom: 4 },
});
