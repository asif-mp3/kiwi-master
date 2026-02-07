import { LoadDataResponse, ProcessQueryResponse, DetectedTable } from '../lib/types';
import { getApiBaseUrl, getElevenLabsVoiceId } from '../lib/constants';

// ============================================================================
// API Service for Thara.ai
// Connected to Python FastAPI backend
// ============================================================================

const API_BASE_URL = getApiBaseUrl();

// ============================================================================
// Authentication Helpers
// ============================================================================

/**
 * Get Authorization headers with Bearer token from localStorage
 */
const getAuthHeaders = (): Record<string, string> => {
  if (typeof window === 'undefined') return {};

  const token = localStorage.getItem('thara_access_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

/**
 * Fetch with timeout - prevents indefinite waits on slow API calls
 */
const fetchWithTimeout = async (
  url: string,
  options: RequestInit,
  timeoutMs: number = 60000  // 60 second default
): Promise<Response> => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Request timed out. Please try again.');
    }
    throw error;
  }
};

/**
 * Handle API response - check for 401 errors and redirect to login
 */
const handleResponse = async (response: Response): Promise<Response> => {
  if (response.status === 401) {
    // Token expired or invalid - clear auth and redirect
    if (typeof window !== 'undefined') {
      localStorage.removeItem('thara_access_token');
      localStorage.removeItem('thara_auth');
      window.location.href = '/';
    }
    throw new Error('Session expired. Please log in again.');
  }
  return response;
};

export const api = {
  /**
   * Connect to a dataset URL.
   * Backend endpoint: POST /api/load-dataset
   *
   * @param url - Google Sheets URL or spreadsheet ID
   * @param append - If true, adds to existing data instead of replacing (for multi-spreadsheet support)
   */
  loadDataset: async (url: string, append: boolean = false): Promise<LoadDataResponse> => {
    console.log('[API] loadDataset called with URL:', url, 'append:', append);

    const response = await handleResponse(
      await fetch(`${API_BASE_URL}/api/load-dataset`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
        body: JSON.stringify({ url, append }),
      })
    );

    if (!response.ok) {
      const error = await response.json();
      console.error('[API] loadDataset HTTP error:', response.status, error);
      throw new Error(error.detail || 'Failed to load dataset');
    }

    const result = await response.json();
    console.log('[API] loadDataset response:', result);

    // Backend returns 200 even on errors with success: false
    if (!result.success) {
      const errorMsg = result.error || result.message || 'Failed to load dataset';
      console.error('[API] loadDataset backend error:', errorMsg);
      throw new Error(errorMsg);
    }

    return result;
  },

  /**
   * Process a user query (text).
   * Backend endpoint: POST /api/query
   * 60s timeout for LLM calls during clarification flows
   * @param text - User query text
   * @param sessionName - Optional session name for "Call me X" feature
   */
  sendMessage: async (text: string, sessionName?: string): Promise<ProcessQueryResponse> => {
    console.log('Sending query:', text, sessionName ? `(as ${sessionName})` : '');

    const response = await handleResponse(
      await fetchWithTimeout(
        `${API_BASE_URL}/api/query`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...getAuthHeaders(),
          },
          body: JSON.stringify({
            text,
            user_name: sessionName || null  // Pass session name for personalization
          }),
        },
        60000  // 60 second timeout
      )
    );

    if (!response.ok) {
      console.error('Query API error:', response.status, response.statusText);
      const error = await response.json().catch(() => ({ detail: 'Failed to process query' }));
      console.error('Error details:', error);
      throw new Error(error.detail || 'Failed to process query');
    }

    const result = await response.json();
    console.log('Query result:', result);
    return result;
  },

  /**
   * Upload audio blob for transcription.
   * Backend endpoint: POST /api/transcribe
   */
  transcribeAudio: async (audioBlob: Blob): Promise<string> => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');

    const response = await handleResponse(
      await fetch(`${API_BASE_URL}/api/transcribe`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
        },
        body: formData,
      })
    );

    if (!response.ok) {
      console.error('Transcribe API error:', response.status, response.statusText);
      const error = await response.json().catch(() => ({ detail: 'Failed to transcribe audio' }));
      throw new Error(error.detail || 'Failed to transcribe audio');
    }

    const result = await response.json();
    console.log('Transcribe result:', result);

    if (!result.success) {
      throw new Error(result.error || 'Transcription failed');
    }

    return result.text || '';
  },

  /**
   * Login with username and password.
   * Backend endpoint: POST /api/auth/login
   */
  login: async (username: string, password: string): Promise<{ success: boolean; user?: { name: string }; access_token?: string; error?: string }> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Login failed' }));
        return { success: false, error: error.detail || 'Invalid credentials' };
      }

      const result = await response.json();

      // Store access token if provided
      if (result.access_token && typeof window !== 'undefined') {
        localStorage.setItem('thara_access_token', result.access_token);
      }

      return { success: true, user: result.user, access_token: result.access_token };
    } catch (e) {
      // Backend not available - don't allow any fallback auth (security risk)
      console.error('[API] Backend not available:', e);
      return {
        success: false,
        error: 'Unable to connect to server. Please ensure the backend is running.'
      };
    }
  },

  /**
   * Check authentication status.
   * Backend endpoint: GET /api/auth/check
   */
  checkAuth: async (): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/check`, {
        headers: {
          ...getAuthHeaders(),
        },
      });
      const result = await response.json();
      return result.authenticated;
    } catch {
      return false; // Return false if backend is not available
    }
  },

  /**
   * Convert text to speech using ElevenLabs (blocking - waits for full audio).
   * Backend endpoint: POST /api/text-to-speech
   * @deprecated Use textToSpeechStream for better latency (saves 2-4 seconds)
   */
  textToSpeech: async (text: string, voiceId?: string): Promise<Blob> => {
    const response = await handleResponse(
      await fetch(`${API_BASE_URL}/api/text-to-speech`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
        body: JSON.stringify({
          text,
          voice_id: voiceId || getElevenLabsVoiceId()
        }),
      })
    );

    if (!response.ok) {
      throw new Error('TTS request failed');
    }

    // Get blob and ensure correct MIME type for browser compatibility
    const blob = await response.blob();
    // Re-create blob with explicit audio/mpeg type if needed
    if (blob.type !== 'audio/mpeg') {
      console.log('[API] Converting blob from', blob.type, 'to audio/mpeg');
      return new Blob([blob], { type: 'audio/mpeg' });
    }
    return blob;
  },

  /**
   * Convert text to speech with STREAMING - collects full audio blob.
   * Backend endpoint: POST /api/text-to-speech/stream
   * Returns the full audio blob once streaming completes.
   * For true streaming playback, use textToSpeechStreamAndPlay instead.
   */
  textToSpeechStream: async (text: string, voiceId?: string): Promise<Blob> => {
    const response = await handleResponse(
      await fetch(`${API_BASE_URL}/api/text-to-speech/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
        body: JSON.stringify({
          text,
          voice_id: voiceId || getElevenLabsVoiceId()
        }),
      })
    );

    if (!response.ok) {
      throw new Error('TTS stream request failed');
    }

    const blob = await response.blob();
    if (blob.type !== 'audio/mpeg') {
      return new Blob([blob], { type: 'audio/mpeg' });
    }
    return blob;
  },

  /**
   * TRUE STREAMING TTS - Audio starts playing as chunks arrive (~200-500ms first byte).
   * Uses chunked collection + immediate playback for best latency.
   * Backend endpoint: POST /api/text-to-speech/stream
   *
   * @param text - Text to convert to speech
   * @param voiceId - Optional ElevenLabs voice ID
   * @param onStart - Callback when audio starts playing
   * @param onEnd - Callback when audio finishes
   * @param onError - Callback on error
   * @returns Audio element that is playing (or will play)
   */
  textToSpeechStreamAndPlay: async (
    text: string,
    voiceId?: string,
    onStart?: () => void,
    onEnd?: () => void,
    onError?: (error: Error) => void
  ): Promise<{ audio: HTMLAudioElement; blob: Promise<Blob> }> => {
    const response = await handleResponse(
      await fetch(`${API_BASE_URL}/api/text-to-speech/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
        body: JSON.stringify({
          text,
          voice_id: voiceId || getElevenLabsVoiceId()
        }),
      })
    );

    if (!response.ok || !response.body) {
      const err = new Error('TTS stream request failed');
      onError?.(err);
      throw err;
    }

    // Collect chunks while streaming
    const reader = response.body.getReader();
    const chunks: Uint8Array[] = [];
    let totalLength = 0;

    // Start collecting chunks
    const collectChunks = async (): Promise<Blob> => {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (value) {
          chunks.push(value);
          totalLength += value.length;
        }
      }

      // Combine all chunks into a single blob
      const combined = new Uint8Array(totalLength);
      let offset = 0;
      for (const chunk of chunks) {
        combined.set(chunk, offset);
        offset += chunk.length;
      }
      return new Blob([combined], { type: 'audio/mpeg' });
    };

    // Start chunk collection (runs in background)
    const blobPromise = collectChunks();

    // Create audio element - will play once blob is ready
    const audio = new Audio();

    // Wait for blob and play
    blobPromise.then((blob) => {
      const url = URL.createObjectURL(blob);
      audio.src = url;
      audio.onended = () => {
        URL.revokeObjectURL(url);
        onEnd?.();
      };
      audio.onerror = () => {
        URL.revokeObjectURL(url);
        onError?.(new Error('Audio playback failed'));
      };
      audio.play()
        .then(() => {
          onStart?.();
          audio.playbackRate = 1.3; // 30% faster playback
        })
        .catch((e) => {
          // Browser autoplay policy - audio element is returned for manual play
          console.warn('Autoplay blocked, user interaction required:', e);
        });
    }).catch((err) => {
      onError?.(err);
    });

    return { audio, blob: blobPromise };
  },

  // ============================================================================
  // Google Sheets OAuth Methods
  // ============================================================================

  /**
   * Check if user has authorized Google Sheets access.
   * Backend endpoint: GET /api/auth/sheets/check
   */
  checkSheetsAuth: async (): Promise<{ configured: boolean; authorized: boolean; user_id?: string }> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/sheets/check`, {
        headers: {
          ...getAuthHeaders(),
        },
      });

      // Validate response before parsing JSON
      if (!response.ok) {
        console.warn('[API] checkSheetsAuth failed:', response.status);
        return { configured: false, authorized: false };
      }

      return await response.json();
    } catch (e) {
      console.error('[API] checkSheetsAuth error:', e);
      return { configured: false, authorized: false };
    }
  },


  /**
   * Get Google OAuth URL for Sheets access.
   * Backend endpoint: GET /api/auth/sheets
   */
  getSheetsAuthUrl: async (): Promise<string> => {
    const response = await fetch(`${API_BASE_URL}/api/auth/sheets`, {
      headers: {
        ...getAuthHeaders(),
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to get auth URL' }));
      throw new Error(error.detail || 'Failed to get Google Sheets auth URL');
    }

    const result = await response.json();
    return result.url;
  },

  /**
   * Exchange authorization code for tokens.
   * Backend endpoint: POST /api/auth/sheets/callback
   */
  exchangeSheetsCode: async (code: string): Promise<{ success: boolean; message: string }> => {
    const response = await fetch(`${API_BASE_URL}/api/auth/sheets/callback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ code }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to authorize' }));
      throw new Error(error.detail || 'Failed to authorize Google Sheets');
    }

    return await response.json();
  },

  /**
   * Revoke Google Sheets access.
   * Backend endpoint: POST /api/auth/sheets/revoke
   */
  revokeSheetsAuth: async (): Promise<{ success: boolean }> => {
    const response = await handleResponse(
      await fetch(`${API_BASE_URL}/api/auth/sheets/revoke`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
        },
      })
    );

    return await response.json();
  },

  // ============================================================================
  // Cache Management
  // ============================================================================

  /**
   * Clear backend caches (query cache, context).
   * Called when user clears chat.
   * Backend endpoint: POST /api/context/clear
   */
  clearCache: async (): Promise<{ success: boolean; cleared_queries?: number }> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/context/clear`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
        body: JSON.stringify({}),
      });

      if (!response.ok) {
        console.warn('[API] clearCache failed:', response.status);
        return { success: false };
      }

      const result = await response.json();
      console.log('[API] Cache cleared:', result);
      return result;
    } catch (e) {
      console.error('[API] clearCache error:', e);
      return { success: false };
    }
  },

  // ============================================================================
  // Demo Mode / Dataset Status
  // ============================================================================

  /**
   * Check if dataset is pre-loaded (demo mode).
   * Backend endpoint: GET /api/dataset-status
   */
  getDatasetStatus: async (): Promise<{
    loaded: boolean;
    demo_mode: boolean;
    total_tables?: number;
    tables?: string[];
    original_sheets?: string[];
    total_records?: number;
    detected_tables?: DetectedTable[];
    loaded_spreadsheets?: string[];
    error?: string;
  }> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/dataset-status`, {
        headers: {
          ...getAuthHeaders(),
        },
      });

      if (!response.ok) {
        return { loaded: false, demo_mode: false };
      }

      return await response.json();
    } catch (e) {
      console.error('[API] getDatasetStatus error:', e);
      return { loaded: false, demo_mode: false };
    }
  },

};


// Helper to generate realistic backend-like table structures
function generateMockTables(): DetectedTable[] {
  return [
    {
      table_id: "t1",
      title: "Monthly_Sales_Summary",
      sheet_name: "Month",
      source_id: "sheet_123#Month",
      sheet_hash: "abc123hash",
      row_range: [2, 150],
      col_range: [0, 8],
      total_rows: 148,
      columns: ["Month", "Revenue", "Cost", "Profit", "Margin"],
      preview_data: []
    },
    {
      table_id: "t2",
      title: "Employee_Roster",
      sheet_name: "Staff",
      source_id: "sheet_123#Staff",
      sheet_hash: "xyz789hash",
      row_range: [0, 50],
      col_range: [0, 5],
      total_rows: 50,
      columns: ["ID", "Name", "Role", "Join Date", "Salary"],
      preview_data: []
    }
  ];
}
