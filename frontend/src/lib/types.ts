export type MessageRole = 'user' | 'assistant' | 'system';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  audioUrl?: string;
  isSpeaking?: boolean;
  metadata?: {
    plan?: QueryPlan | null;
    data?: any[] | null;
    schema_context?: { text: string }[];
    data_refreshed?: boolean;
    is_greeting?: boolean;
    is_memory_storage?: boolean;
  };
}

export interface ChatTab {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
  // Per-chat Dataset Context
  datasetUrl: string | null;
  datasetStatus: 'unconnected' | 'loading' | 'ready';
  datasetStats?: {
    totalTables: number;
    totalRecords: number;
    sheetCount: number;
    sheets: string[];
    detectedTables: DetectedTable[]; // Detailed backend detected tables
  };
}

// Backend-aligned Query Plan Schema (from plan_schema.json)
export interface QueryPlan {
  query_type: 'metric' | 'lookup' | 'filter' | 'extrema_lookup' | 'rank' | 'list' | 'aggregation_on_subset';
  table: string;
  select_columns?: string[] | null;
  metrics?: string[] | null;
  filters?: {
    column: string;
    operator: '=' | '>' | '<' | '>=' | '<=' | '!=' | 'LIKE';
    value: any;
  }[];
  group_by?: string[];
  order_by?: {
    column: string;
    direction: 'ASC' | 'DESC';
  }[]; // The backend is actually array of arrays [[col, dir], ...], but frontend usually simplifies. 
  // UPDATE: Backend schema says: Items: [string, string("ASC"|"DESC")]
  limit?: number;
  aggregation_function?: string;
  aggregation_column?: string | null;
  subset_filters?: any[];
  subset_order_by?: any[];
  subset_limit?: number | null;
}

// Backend-aligned Table Detection Schema (from connector.py)
export interface DetectedTable {
  table_id: string;
  title?: string;
  sheet_name: string;
  source_id: string; // spreadsheet_id#sheet_name
  sheet_hash: string;
  row_range: [number, number];
  col_range: [number, number];
  // Frontend will handle dataframe as array of objects (JSON representation)
  preview_data?: any[];
  total_rows?: number;
  columns?: string[];
}

export interface AuthState {
  isAuthenticated: boolean;
  username: string | null;
}

export interface AppConfig {
  googleSheetUrl: string | null;
}
