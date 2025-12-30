/**
 * API Client for Kiwi Backend
 * Handles all communication between frontend and FastAPI middleware
 */

// Import from shared folder at monorepo root
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Centralized endpoint definition - Single source of truth
const ENDPOINTS = {
  HEALTH: `${API_BASE_URL}/`,
  CHAT: `${API_BASE_URL}/api/chat/query`,
  SHEETS_CONNECT: `${API_BASE_URL}/api/sheets/connect`,
  SHEETS_STATUS: `${API_BASE_URL}/api/sheets/status`,
  SHEETS_SUMMARY: `${API_BASE_URL}/api/sheets/summary`,
  SESSION_RESET: `${API_BASE_URL}/api/session/reset`,
  VOICE_TRANSCRIBE: `${API_BASE_URL}/api/voice/transcribe`,
  VOICE_SYNTHESIZE: `${API_BASE_URL}/api/voice/synthesize`,
} as const;

export interface ChatRequest {
  message: string;
  conversationId?: string;
}

export interface ChatResponse {
  message: string;
  conversationId: string;
  timestamp: string;
  metadata?: {
    success: boolean;
    query_plan?: any;
    result_count?: number;
    schema_context?: string[];
  };
}

export interface SheetConnectionRequest {
  sheet_url: string;
}

export interface SheetConnectionResponse {
  success: boolean;
  message: string;
  file_id?: string;
  sheet_name?: string;
}


class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }

  /**
   * Send a chat message to the RAG pipeline
   */
  async sendMessage(
    message: string,
    conversationId?: string
  ): Promise<ChatResponse> {
    const response = await fetch(ENDPOINTS.CHAT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: message,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      let errorMessage = error.detail || 'Failed to send message';

      // Handle structured error objects from backend
      if (typeof errorMessage === 'object') {
        errorMessage = errorMessage.message || errorMessage.error || JSON.stringify(errorMessage);
      }

      throw new Error(errorMessage);
    }

    const data = await response.json();

    // Adapt backend response to frontend format
    return {
      message: data.answer,
      conversationId: conversationId || 'default',
      timestamp: new Date().toISOString(),
      metadata: {
        success: true,
        query_plan: data.query_plan,
        result_count: data.result_data?.rows ? data.result_data.rows.length : 0,
        schema_context: data.schema_context
      }
    };
  }

  /**
   * Connect to a Google Sheet using robust, native-like SSE handling.
   * 
   * Note: Standard EventSource does not support POST requests.
   * We stick to fetch + ReadableStream for the cleanest implementation that
   * respects the backend's SSE format while allowing a POST body (for the URL).
   */
  async connectSheet(
    sheetUrl: string,
    onProgress?: (data: { message: string; stage: string }) => void
  ): Promise<SheetConnectionResponse> {

    return new Promise((resolve, reject) => {
      fetch(ENDPOINTS.SHEETS_CONNECT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream'
        },
        body: JSON.stringify({ sheet_url: sheetUrl })
      }).then(async (response) => {
        if (!response.ok) {
          const error = await response.json();
          reject(new Error(error.detail || 'Failed to connect'));
          return;
        }

        if (!response.body) {
          reject(new Error('No response body from server'));
          return;
        }

        // Robust SSE Reader
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          buffer += chunk;

          // Split by double newline which marks end of SSE event
          const parts = buffer.split('\n\n');
          buffer = parts.pop() || ''; // Keep incomplete part in buffer

          for (const part of parts) {
            const lines = part.split('\n');
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const jsonStr = line.substring(6);
                  const data = JSON.parse(jsonStr);

                  if (onProgress) {
                    onProgress({
                      message: data.message || data.stage,
                      stage: data.stage
                    });
                  }

                  if (data.stage === 'READY') {
                    // Final success state
                    resolve({
                      success: true,
                      message: 'Connected successfully',
                      sheet_name: 'Google Sheet'
                    });
                    return; // Exit loop
                  }

                  if (data.stage === 'ERROR') {
                    reject(new Error(data.error || 'Unknown backend error'));
                    return;
                  }
                } catch (e) {
                  console.error('Error parsing SSE data line:', line, e);
                }
              }
            }
          }
        }
      }).catch(error => {
        console.error('Fetch error during SSE:', error);
        reject(error);
      });
    });
  }

  /**
   * Get load status
   */
  async getSheetStatus(): Promise<{ is_loaded: boolean; sheet_url: string | null; success: boolean }> {
    try {
      const response = await fetch(ENDPOINTS.SHEETS_STATUS);
      if (!response.ok) throw new Error('Failed');
      const data = await response.json();

      return {
        is_loaded: data.status === 'READY',
        sheet_url: null,
        success: true
      };
    } catch (e) {
      return { is_loaded: false, sheet_url: null, success: false };
    }
  }

  /**
   * Get details (metadata)
   */
  async getSheetDetails(): Promise<any> {
    const response = await fetch(ENDPOINTS.SHEETS_SUMMARY);
    if (!response.ok) throw new Error('Failed to get details');
    const data = await response.json();

    // Adapt format to what frontend expects if needed, or pass through
    const totalTables = data.sheets.reduce((acc: number, s: any) => acc + s.tables.length, 0);
    const totalRows = data.sheets.reduce((acc: number, s: any) =>
      acc + s.tables.reduce((tAcc: number, t: any) => tAcc + t.row_count, 0), 0
    );

    const sheets = data.sheets.map((s: any) => ({
      ...s,
      tables: s.tables.map((t: any) => ({
        ...t,
        types: t.columns.map(() => 'text') // Metadata-only; types not always available
      }))
    }));

    return {
      success: true,
      total_tables: totalTables,
      total_rows: totalRows,
      sheet_count: data.sheets.length,
      sheets: sheets
    };
  }

  /**
   * Reset the current session in backend
   */
  async resetSession(): Promise<void> {
    await fetch(ENDPOINTS.SESSION_RESET, { method: 'POST' });
  }

  /**
   * Transcribe audio using the new Voice Router
   */
  async transcribeAudio(audioBlob: Blob): Promise<{ text: string; language: string }> {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');

    // Send language hint if we have one? For now, let Whisper detect.

    // Uses the new standardized /api/voice/transcribe endpoint
    const response = await fetch(ENDPOINTS.VOICE_TRANSCRIBE, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      let errorMessage = error.detail || 'Failed to transcribe audio';
      if (typeof errorMessage === 'object') {
        errorMessage = errorMessage.message || JSON.stringify(errorMessage);
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.message || 'Transcription failed');
    }

    return {
      text: data.text,
      language: data.language || 'en'
    };
  }

  /**
   * Synthesize speech using the new Voice Router
   * Note: This returns a Blob (MP3 audio), not JSON.
   */
  /* 
   * CURRENTLY NOT USED BY FRONTEND (It uses local ElevenLabs logic or similar?)
   * Wait -> We stripped local logic. We need this now.
   * But audio-player.ts might handle the fetch itself. 
   * Let's expose the URL or a function to get the blob.
   */
  getSynthesisUrl(text: string): string {
    // Return URL for audio src
    // Not strictly REST but useful for <audio src="...">
    return `${ENDPOINTS.VOICE_SYNTHESIZE}?text=${encodeURIComponent(text)}`;
  }
}

export const apiClient = new ApiClient();
