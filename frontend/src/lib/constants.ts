/**
 * Application constants for Thara.ai
 */

export const APP_NAME = 'Thara.ai';
export const APP_VERSION = '2.0.0';

// Voice recording timeouts
export const VOICE_RECORDING_TIMEOUT = 10000; // 10 seconds auto-stop
export const VOICE_MODE_TIMEOUT = 30000; // 30 seconds before disabling voice mode
export const TTS_COMPLETION_WAIT = 1500; // Wait time after TTS playback

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
