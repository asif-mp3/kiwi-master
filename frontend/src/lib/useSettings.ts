'use client';

import { useState, useEffect, useCallback } from 'react';

export interface AppSettings {
  voiceSpeed: number;        // 0.5 - 2.0
  defaultChartType: 'auto' | 'bar' | 'line' | 'pie';
  textSize: 'small' | 'medium' | 'large';
  autoPlayVoice: boolean;
  language: 'en' | 'ta' | 'auto';
}

const DEFAULT_SETTINGS: AppSettings = {
  voiceSpeed: 1.0,
  defaultChartType: 'auto',
  textSize: 'medium',
  autoPlayVoice: false,
  language: 'auto',
};

const SETTINGS_KEY = 'thara_settings';

export function useSettings() {
  const [settings, setSettingsState] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load settings from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(SETTINGS_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        setSettingsState({ ...DEFAULT_SETTINGS, ...parsed });
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
    setIsLoaded(true);
  }, []);

  // Save settings to localStorage
  const setSettings = useCallback((newSettings: Partial<AppSettings>) => {
    setSettingsState(prev => {
      const updated = { ...prev, ...newSettings };
      try {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(updated));
      } catch (error) {
        console.error('Failed to save settings:', error);
      }
      return updated;
    });
  }, []);

  // Reset to defaults
  const resetSettings = useCallback(() => {
    setSettingsState(DEFAULT_SETTINGS);
    try {
      localStorage.removeItem(SETTINGS_KEY);
    } catch (error) {
      console.error('Failed to reset settings:', error);
    }
  }, []);

  return {
    settings,
    setSettings,
    resetSettings,
    isLoaded,
  };
}
