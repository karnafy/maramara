import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import * as Localization from "expo-localization";
import he from "./he.json";
import en from "./en.json";

const deviceLang = Localization.getLocales()[0]?.languageCode || "he";
const supported = ["he", "en"];
const defaultLang = supported.includes(deviceLang) ? deviceLang : "he";

i18n.use(initReactI18next).init({
  resources: {
    he: { translation: he },
    en: { translation: en },
  },
  lng: defaultLang,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export default i18n;
