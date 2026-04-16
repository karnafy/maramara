import { useState } from "react";
import { View, Text, TouchableOpacity, StyleSheet, Alert } from "react-native";
import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import { colors, spacing, radii, typography } from "../utils/theme";
import { api } from "../services/api";

const PROMPTS = [
  { duration: 10, prompt_he: "ספר על יום רגיל שלך", prompt_en: "Talk about a normal day" },
  { duration: 12, prompt_he: "איזה מקום אתה הכי אוהב", prompt_en: "Your favourite place" },
  { duration: 13, prompt_he: "תאר תחושה שהרגשת השבוע", prompt_en: "A feeling from this week" },
];

export default function Onboarding() {
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [recording, setRecording] = useState(false);

  const currentPrompt = PROMPTS[step];

  const record = async () => {
    // TODO: integrate expo-audio
    setRecording(true);
    setTimeout(async () => {
      setRecording(false);
      if (step + 1 < PROMPTS.length) {
        setStep(step + 1);
      } else {
        try {
          await api.voice.completeEnrollment();
          router.replace("/(tabs)/home");
        } catch (e: any) {
          Alert.alert(t("common.error"), e.message);
        }
      }
    }, (currentPrompt?.duration || 10) * 1000);
  };

  if (!currentPrompt) return null;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t("onboarding.title")}</Text>
      <Text style={styles.stepIndicator}>{step + 1} / {PROMPTS.length}</Text>

      <View style={styles.promptBox}>
        <Text style={styles.prompt}>
          {i18n.language === "he" ? currentPrompt.prompt_he : currentPrompt.prompt_en}
        </Text>
        <Text style={styles.duration}>{currentPrompt.duration} {t("onboarding.seconds")}</Text>
      </View>

      <TouchableOpacity
        style={[styles.recordButton, recording && styles.recordButtonActive]}
        onPress={record}
        disabled={recording}
      >
        <Text style={styles.recordButtonText}>
          {recording ? t("onboarding.recording") : t("onboarding.tapToRecord")}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: spacing.xl, backgroundColor: colors.bg },
  title: { ...typography.h1, textAlign: "center", color: colors.primary, marginBottom: spacing.sm },
  stepIndicator: { textAlign: "center", color: colors.textMuted, marginBottom: spacing.xl },
  promptBox: { backgroundColor: colors.surface, padding: spacing.xl, borderRadius: radii.lg, marginBottom: spacing.xl },
  prompt: { fontSize: 22, fontWeight: "600", color: colors.text, textAlign: "center", marginBottom: spacing.md },
  duration: { textAlign: "center", color: colors.textMuted },
  recordButton: { backgroundColor: colors.primary, padding: spacing.lg, borderRadius: radii.full, alignItems: "center" },
  recordButtonActive: { backgroundColor: colors.danger },
  recordButtonText: { color: "#fff", fontSize: 18, fontWeight: "600" },
});
