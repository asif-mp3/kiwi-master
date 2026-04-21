/**
 * Application constants for Thara.ai
 */

export const APP_NAME = 'Thara.ai';
export const APP_VERSION = '2.0.0';

// Voice recording timeouts
export const VOICE_RECORDING_TIMEOUT = 15000; // 15 seconds max recording (fallback)
export const VOICE_MODE_TIMEOUT = 30000; // 30 seconds before disabling voice mode
export const TTS_COMPLETION_WAIT = 1500; // Wait time after TTS playback
export const NO_SPEECH_CANCEL_TIMEOUT = 10000; // Cancel voice mode if no audio detected within 10s

// Voice Activity Detection (VAD) settings
// Using speech-band energy (300-3000 Hz only) instead of full-spectrum average.
// This is far more accurate — a simple full-spectrum average is always diluted
// by silent high-frequency bins even during active speech.
export const VAD_SILENCE_THRESHOLD = 15; // Speech-band RMS below this = silence
export const VAD_SILENCE_DURATION = 1200; // Stop after 1.2s of silence (more forgiving)
export const VAD_MIN_SPEECH_DURATION = 400; // Min recording before silence check (ms)
export const VAD_CHECK_INTERVAL = 50; // How often to check audio levels (ms)

// API URLs — production URL MUST come from env var (NEXT_PUBLIC_API_BASE_URL)
const LOCALHOST_API_URL = 'http://localhost:8000';

export const DEFAULT_SESSION_NAME = 'Boss';

// Get environment variables with fallbacks
export const getApiBaseUrl = () => {
  // Always prefer environment variable (set in Vercel dashboard)
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }

  // Auto-detect localhost for development
  if (typeof window !== 'undefined') {
    const isLocalhost = window.location.hostname === 'localhost' ||
                        window.location.hostname === '127.0.0.1';
    if (isLocalhost) {
      return LOCALHOST_API_URL;
    }
  }

  // Production: MUST be set via NEXT_PUBLIC_API_BASE_URL env var
  return LOCALHOST_API_URL;
};

export const getElevenLabsVoiceId = () => {
  return process.env.NEXT_PUBLIC_ELEVENLABS_VOICE_ID || '';
};
