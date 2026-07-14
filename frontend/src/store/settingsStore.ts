import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { UserSettings } from "@/types";

const DEFAULT_SETTINGS: UserSettings = {
  default_marks: 1,
  shuffle_questions: false,
  shuffle_options: false,
  theme: "system",
  language: "en",
  default_difficulty: "",
  autosave_interval: 5,
};

interface SettingsStore {
  settings: UserSettings;
  updateSettings: (updates: Partial<UserSettings>) => void;
  resetSettings: () => void;
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      settings: DEFAULT_SETTINGS,
      updateSettings: (updates) =>
        set((state) => ({ settings: { ...state.settings, ...updates } })),
      resetSettings: () => set({ settings: DEFAULT_SETTINGS }),
    }),
    { name: "quizgen-settings" }
  )
);
