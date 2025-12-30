/**
 * Enhanced API Client for kiwi-master with WebSocket support
 * Production-grade integration with advanced error handling
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

import type {
  DatasetMetadata,
  QueryRequest,
  QueryResponse,
  LoadingStage
} from "./dataset-types";

// WebSocket progress update interface
export interface ProgressUpdate {
  stage: LoadingStage;
  message: string;
  progress?: number;
}

/**
 * Singleton API Client
 */
class APIClient {
  private static instance: APIClient;

  private constructor() { }

  static getInstance(): APIClient {
    if (!APIClient.instance) {
      APIClient.instance = new APIClient();
    }
    return APIClient.instance;
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/`);
      if (!response.ok) throw new Error('API server not responding');
      return response.json();
    } catch (error) {
      console.error('Health check failed:', error);
      throw new Error('Cannot connect to API server. Is it running on port 8000?');
    }
  }

  /**
   * Connect to dataset with real-time SSE progress
   * Returns EventSource for listening to stages
   */
  connectSheet(sheetUrl?: string): EventSource {
    const url = `${API_BASE_URL}/sheets/connect`;
    console.log('[API] Connecting to sheet via SSE:', url);

    const eventSource = new EventSource(url, { withCredentials: false });
    return eventSource;
  }

  /**
   * Get dataset status
   */
  async getSheetsStatus(): Promise<{
    status: string;
    current_stage: string | null;
    error?: string;
  }> {
    const response = await fetch(`${API_BASE_URL}/sheets/status`);
    if (!response.ok) throw new Error(`Status check failed: ${response.statusText}`);
    return response.json();
  }

  /**
   * Get dataset summary (metadata-only, <100ms expected)
   */
  async getSheetsSummary(): Promise<DatasetMetadata> {
    const startTime = performance.now();
    console.log('[API] Fetching dataset summary...');

    const response = await fetch(`${API_BASE_URL}/sheets/summary`);
    const endTime = performance.now();
    const duration = endTime - startTime;

    // Warn if took too long (backend might be computing instead of reading metadata)
    if (duration > 500) {
      console.warn(`⚠️ /sheets/summary took ${duration.toFixed(0)}ms - backend may be computing!`);
    } else {
      console.log(`✓ Dataset summary fetched in ${duration.toFixed(0)}ms`);
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || response.statusText);
    }

    return response.json();
  }

  /**
   * Send query to backend
   */
  async sendQuery(question: string): Promise<QueryResponse> {
    console.log('[API] Sending query:', question);
    const request: QueryRequest = { question };

    const response = await fetch(`${API_BASE_URL}/chat/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      const error = await response.json();
      const errorMsg = error.detail?.error || error.detail || response.statusText;
      console.error('[API] Query failed:', errorMsg);
      throw new Error(errorMsg);
    }

    const result = await response.json();
    console.log('[API] Query successful, execution time:', result.metadata?.execution_time);
    return result;
  }

  /**
   * Reset session (clears backend state)
   */
  async resetSession(): Promise<{ status: string }> {
    console.log('[API] Resetting session...');
    const response = await fetch(`${API_BASE_URL}/session/reset`, { method: "POST" });

    if (!response.ok) {
      throw new Error(`Reset failed: ${response.statusText}`);
    }

    const result = await response.json();
    console.log('[API] Session reset successful');
    return result;
  }
}

// Export singleton instance
export const apiClient = APIClient.getInstance();

// Re-export individual functions for convenience
export const healthCheck = () => apiClient.healthCheck();
export const connectSheet = (url?: string) => apiClient.connectSheet(url);
export const getSheetsStatus = () => apiClient.getSheetsStatus();
export const getSheetsSummary = () => apiClient.getSheetsSummary();
export const sendQuery = (question: string) => apiClient.sendQuery(question);
export const resetSession = () => apiClient.resetSession();
