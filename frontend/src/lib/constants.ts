/**
 * Application constants for Thara.ai
 */

export const APP_NAME = 'Thara.ai';
export const APP_VERSION = '2.0.0';

// Voice recording timeouts
export const VOICE_RECORDING_TIMEOUT = 15000; // 15 seconds max recording (fallback)
export const VOICE_MODE_TIMEOUT = 30000; // 30 seconds before disabling voice mode
export const TTS_COMPLETION_WAIT = 1500; // Wait time after TTS playback

// Voice Activity Detection (VAD) settings for phone-call-like experience
export const VAD_SILENCE_THRESHOLD = 12; // Audio level below this = silence (lower = more sensitive)
export const VAD_SILENCE_DURATION = 1000; // Stop after 1 second of silence (faster response)
export const VAD_MIN_SPEECH_DURATION = 250; // Minimum speech before checking silence (ms)
export const VAD_CHECK_INTERVAL = 50; // How often to check audio levels (ms) - faster polling

// API defaults
export const DEFAULT_API_BASE_URL = 'http://localhost:8000';

// Get environment variables with fallbacks
export const getApiBaseUrl = () =>
  process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL;

export const getElevenLabsVoiceId = () => {
  const voiceId = process.env.NEXT_PUBLIC_ELEVENLABS_VOICE_ID;
  if (!voiceId) {
    console.warn('NEXT_PUBLIC_ELEVENLABS_VOICE_ID not set - voice features may not work');
    return ''; // Return empty instead of hardcoded fallback
  }
  return voiceId;
};
