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
    visualization?: VisualizationConfig | null;
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

// Filter condition type
export interface FilterCondition {
  column: string;
  operator: '=' | '>' | '<' | '>=' | '<=' | '!=' | 'LIKE';
  value: string | number | boolean | null;
}

// Order by specification - backend uses [column, direction] tuples
export type OrderBySpec = [string, 'ASC' | 'DESC'];

// Backend-aligned Query Plan Schema (from plan_schema.json)
export interface QueryPlan {
  query_type: 'metric' | 'lookup' | 'filter' | 'extrema_lookup' | 'rank' | 'list' | 'aggregation_on_subset';
  table: string;
  select_columns?: string[] | null;
  metrics?: string[] | null;
  filters?: FilterCondition[];
  group_by?: string[];
  order_by?: OrderBySpec[];
  limit?: number;
  aggregation_function?: string;
  aggregation_column?: string | null;
  subset_filters?: FilterCondition[];
  subset_order_by?: OrderBySpec[];
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

// API Response Types
export interface LoadDataResponse {
  success: boolean;
  stats?: {
    totalTables: number;
    totalRecords: number;
    sheetCount: number;
    sheets: string[];
    detectedTables: DetectedTable[];
    profiledTables?: number;
    loadedSpreadsheets?: string[];  // List of all loaded spreadsheet IDs (for multi-spreadsheet support)
  };
  error?: string;
  data_summary?: string;
  total_tables?: number;
  total_sheets?: number;
}

// Visualization configuration for charts
export interface VisualizationDataPoint {
  name: string;
  value: number;
  projected?: boolean;  // True for forecast/projection data points
}

export interface VisualizationConfig {
  type: 'bar' | 'line' | 'pie' | 'horizontal_bar';
  title: string;
  data: VisualizationDataPoint[];
  xKey?: string;
  yKey?: string;
  colors: string[];
  isProjection?: boolean;  // True if chart contains projection data
}

export interface ProcessQueryResponse {
  success: boolean;
  explanation?: string;
  data?: Record<string, unknown>[];
  plan?: QueryPlan;
  schema_context?: { text: string }[];
  data_refreshed?: boolean;
  error?: string;
  is_greeting?: boolean;
  is_memory_storage?: boolean;
  table_used?: string;
  routing_confidence?: number;
  was_followup?: boolean;
  entities_extracted?: Record<string, unknown>;
  healing_attempts?: { attempt: number; error: string; fix: string }[];
  visualization?: VisualizationConfig;
}

export interface DatasetStatusResponse {
  loaded: boolean;
  demo_mode: boolean;
  total_tables?: number;
  tables?: string[];
  error?: string;
}

export interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  version: string;
  checks: {
    [key: string]: {
      status: 'ok' | 'warning' | 'error';
      message?: string;
      [key: string]: unknown;
    };
  };
}
