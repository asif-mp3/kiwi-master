export type MessageRole = 'user' | 'assistant' | 'system';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  audioUrl?: string;
  isSpeaking?: boolean;
}

export interface ChatTab {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
  sheetUrl?: string; // Persisted sheet URL
  sheetName?: string; // Persisted sheet Name
}

export interface ChatSession {
  messages: Message[];
}

export interface AuthState {
  isAuthenticated: boolean;
  username: string | null;
}

export interface AppConfig {
  googleSheetUrl: string | null;
}
