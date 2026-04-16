import { Tabs } from "expo-router";
import { useTranslation } from "react-i18next";
import { colors } from "../../utils/theme";

export default function TabsLayout() {
  const { t } = useTranslation();
  return (
    <Tabs screenOptions={{ tabBarActiveTintColor: colors.primary, headerStyle: { backgroundColor: colors.surface } }}>
      <Tabs.Screen name="home" options={{ title: t("nav.home") }} />
      <Tabs.Screen name="timeline" options={{ title: t("nav.timeline") }} />
      <Tabs.Screen name="insights" options={{ title: t("nav.insights") }} />
      <Tabs.Screen name="listen" options={{ title: t("nav.listen") }} />
      <Tabs.Screen name="settings" options={{ title: t("nav.settings") }} />
    </Tabs>
  );
}
