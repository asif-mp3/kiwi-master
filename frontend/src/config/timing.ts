/**
 * Centralized timing constants for the application.
 * All timeouts, delays, and intervals in one place.
 */

// API request timeouts (ms)
export const API_TIMEOUTS = {
  DEFAULT: 60000,        // 60s — standard API calls
  QUERY: 60000,          // 60s — LLM query processing
  UPLOAD: 120000,        // 2 min — file uploads
  SYNC_FOLDER: 120000,   // 2 min — folder sync
  LOAD_SOURCE: 60000,    // 60s — load data source
} as const;

// Session management
export const SESSION = {
  TIMEOUT_MS: 3600 * 1000,    // 1 hour inactivity timeout
  ACTIVITY_THROTTLE_MS: 10000, // 10s between activity updates
  EXPIRY_CHECK_INTERVAL_MS: 30000, // 30s between session expiry checks
} as const;

// Chat UI animations
export const ANIMATION = {
  TYPING_CHAR_DELAY_MS: 50,       // Typing effect character delay
  TYPING_PAUSE_BEFORE_ERASE_MS: 2000, // Pause before erasing text
  ERASE_CHAR_DELAY_MS: 30,        // Character erase delay
  WORD_ANIMATION_DELAY_MS: 80,    // Word-by-word animation
  CAPTION_CLEAR_DELAY_MS: 5000,   // Clear live captions after TTS
  TTS_CAPTION_CLEAR_MS: 2000,     // Clear caption after TTS ends
  RESUME_RECORDING_DELAY_MS: 100, // Delay before resuming recording
  ABORT_FLAG_RESET_MS: 100,       // Abort flag reset delay
} as const;

// Scroll timing
export const SCROLL_DELAYS = {
  IMMEDIATE: 50,
  SHORT: 150,
  MEDIUM: 350,
  LONG: 600,
} as const;

// Audio/TTS
export const AUDIO = {
  TTS_PLAYBACK_RATE: 1.1,         // 10% faster playback
  AUDIO_MIME_TYPE: 'audio/webm;codecs=opus',
} as const;
