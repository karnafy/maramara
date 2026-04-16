import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../hooks/useAuth";
import { colors, spacing, radii, typography } from "../../utils/theme";

export default function Settings() {
  const { t, i18n } = useTranslation();
  const { signOut } = useAuth();

  return (
    <View style={styles.container}>
      <Text style={typography.h2}>{t("settings.title")}</Text>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>{t("settings.language")}</Text>
        <View style={styles.row}>
          {["he", "en"].map(lang => (
            <TouchableOpacity
              key={lang}
              style={[styles.pill, i18n.language === lang && styles.pillActive]}
              onPress={() => i18n.changeLanguage(lang)}
            >
              <Text style={[styles.pillText, i18n.language === lang && styles.pillTextActive]}>
                {lang === "he" ? "עברית" : "English"}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <TouchableOpacity style={styles.dangerButton} onPress={signOut}>
        <Text style={styles.dangerText}>{t("settings.signOut")}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: spacing.lg, backgroundColor: colors.bg },
  section: { marginVertical: spacing.lg },
  sectionTitle: { fontWeight: "600", marginBottom: spacing.sm },
  row: { flexDirection: "row", gap: spacing.sm },
  pill: { paddingVertical: spacing.sm, paddingHorizontal: spacing.md, borderRadius: radii.full, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
  pillActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  pillText: { color: colors.text },
  pillTextActive: { color: "#fff" },
  dangerButton: { marginTop: "auto", padding: spacing.md, borderRadius: radii.md, borderWidth: 1, borderColor: colors.danger },
  dangerText: { color: colors.danger, textAlign: "center", fontWeight: "600" },
});
