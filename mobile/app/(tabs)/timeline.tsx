import { View, Text, StyleSheet } from "react-native";
import { useTranslation } from "react-i18next";
import { colors, spacing, typography } from "../../utils/theme";

export default function Timeline() {
  const { t } = useTranslation();
  return (
    <View style={styles.container}>
      <Text style={typography.h2}>{t("timeline.title")}</Text>
      <Text style={styles.subtitle}>{t("timeline.subtitle")}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: spacing.lg, backgroundColor: colors.bg },
  subtitle: { color: colors.textMuted, marginTop: spacing.sm },
});
