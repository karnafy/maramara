import { useState } from "react";
import { View, Text, TouchableOpacity, StyleSheet, Animated } from "react-native";
import { useTranslation } from "react-i18next";
import { colors, spacing, radii, typography } from "../../utils/theme";

export default function Listen() {
  const { t } = useTranslation();
  const [listening, setListening] = useState(false);

  return (
    <View style={styles.container}>
      <Text style={typography.h2}>{t("listen.title")}</Text>
      <Text style={styles.subtitle}>{t("listen.subtitle")}</Text>

      <View style={styles.ring}>
        <View style={[styles.innerRing, listening && styles.innerRingActive]}>
          <Text style={styles.ringIcon}>🎙️</Text>
        </View>
      </View>

      <Text style={styles.statusLabel}>
        {listening ? t("listen.listening") : t("listen.ready")}
      </Text>

      <TouchableOpacity
        style={[styles.button, listening && styles.buttonStop]}
        onPress={() => setListening(!listening)}
      >
        <Text style={styles.buttonText}>
          {listening ? t("listen.stop") : t("listen.start")}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", alignItems: "center", padding: spacing.xl, backgroundColor: colors.bg },
  subtitle: { textAlign: "center", color: colors.textMuted, marginVertical: spacing.md, maxWidth: 320 },
  ring: { width: 200, height: 200, borderRadius: 100, justifyContent: "center", alignItems: "center", backgroundColor: colors.primaryLight, marginVertical: spacing.xl },
  innerRing: { width: 140, height: 140, borderRadius: 70, backgroundColor: colors.surface, justifyContent: "center", alignItems: "center", borderWidth: 3, borderColor: colors.border },
  innerRingActive: { borderColor: colors.positive, backgroundColor: "#dcfce7" },
  ringIcon: { fontSize: 56 },
  statusLabel: { fontWeight: "600", fontSize: 18, marginBottom: spacing.lg },
  button: { backgroundColor: colors.primary, paddingVertical: spacing.md, paddingHorizontal: spacing.xl, borderRadius: radii.full },
  buttonStop: { backgroundColor: colors.danger },
  buttonText: { color: "#fff", fontSize: 18, fontWeight: "600" },
});
