/**
 * Centralized localStorage key definitions.
 * Single source of truth — never use string literals for storage keys elsewhere.
 */

export const STORAGE_KEYS = {
  AUTH: 'thara_auth',
  ACCESS_TOKEN: 'thara_access_token',
  CHAT: 'thara_chat',
  CONFIG: 'thara_config',
  TABS: 'thara_tabs',
  LAST_ACTIVITY: 'thara_last_activity',
  SESSION_NAME: 'thara_session_name',
  SETTINGS: 'thara_settings',
} as const;

export type StorageKey = typeof STORAGE_KEYS[keyof typeof STORAGE_KEYS];
