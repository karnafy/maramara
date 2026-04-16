import { useEffect } from "react";
import { Redirect } from "expo-router";
import { useAuth } from "../hooks/useAuth";
import { View, ActivityIndicator } from "react-native";

export default function Index() {
  const { user, loading, profile } = useAuth();

  if (loading) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
        <ActivityIndicator size="large" color="#4F46E5" />
      </View>
    );
  }

  if (!user) return <Redirect href="/auth" />;
  if (!profile?.onboarding_completed) return <Redirect href="/onboarding" />;
  return <Redirect href="/(tabs)/home" />;
}
