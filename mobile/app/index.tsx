import { Redirect } from "expo-router";

// DEV: auth bypass for Impeccable redesign work. Restore from git before shipping.
export default function Index() {
  return <Redirect href="/(tabs)/home" />;
}
