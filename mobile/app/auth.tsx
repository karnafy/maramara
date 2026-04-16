import { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, Alert, StyleSheet } from "react-native";
import { useRouter } from "expo-router";
import { useTranslation } from "react-i18next";
import { useAuth } from "../hooks/useAuth";
import { colors, spacing, radii, typography } from "../utils/theme";

export default function AuthScreen() {
  const { t } = useTranslation();
  const router = useRouter();
  const { signIn, signUp } = useAuth();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setLoading(true);
    try {
      if (mode === "signup") {
        await signUp({ email, password, full_name: fullName });
        Alert.alert(t("auth.signupSuccess"), t("auth.checkEmail"));
        setMode("login");
      } else {
        await signIn({ email, password });
        router.replace("/");
      }
    } catch (e: any) {
      Alert.alert(t("common.error"), e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.logo}>🪞</Text>
      <Text style={styles.title}>MARAMARA</Text>
      <Text style={styles.subtitle}>
        {mode === "login" ? t("auth.welcomeBack") : t("auth.joinUs")}
      </Text>

      {mode === "signup" && (
        <TextInput
          style={styles.input}
          placeholder={t("auth.fullName") || ""}
          value={fullName}
          onChangeText={setFullName}
          autoComplete="name"
        />
      )}
      <TextInput
        style={styles.input}
        placeholder={t("auth.email") || ""}
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
        autoComplete="email"
      />
      <TextInput
        style={styles.input}
        placeholder={t("auth.password") || ""}
        value={password}
        onChangeText={setPassword}
        secureTextEntry
      />

      <TouchableOpacity style={styles.button} onPress={submit} disabled={loading}>
        <Text style={styles.buttonText}>
          {loading ? "..." : mode === "login" ? t("auth.signIn") : t("auth.signUp")}
        </Text>
      </TouchableOpacity>

      <TouchableOpacity onPress={() => setMode(mode === "login" ? "signup" : "login")}>
        <Text style={styles.switchText}>
          {mode === "login" ? t("auth.needAccount") : t("auth.haveAccount")}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: spacing.xl, backgroundColor: colors.bg },
  logo: { fontSize: 64, textAlign: "center", marginBottom: spacing.md },
  title: { ...typography.h1, textAlign: "center", color: colors.primary },
  subtitle: { ...typography.body, textAlign: "center", color: colors.textMuted, marginBottom: spacing.xl },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.md,
    padding: spacing.md,
    marginBottom: spacing.md,
    fontSize: 16,
    backgroundColor: colors.surface,
  },
  button: {
    backgroundColor: colors.primary,
    padding: spacing.md,
    borderRadius: radii.md,
    alignItems: "center",
    marginTop: spacing.sm,
  },
  buttonText: { color: "#fff", fontWeight: "600", fontSize: 16 },
  switchText: { textAlign: "center", marginTop: spacing.md, color: colors.primary },
});
