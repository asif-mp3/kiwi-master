export type MessageRole = 'user' | 'assistant' | 'system';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  audioUrl?: string;
  isSpeaking?: boolean;
  metadata?: {
    plan?: QueryPlan | null;
    data?: Record<string, unknown>[] | null;
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

// Backend-aligned Query Plan Schema (from plan_schema.json and models.py)
export interface QueryPlan {
  query_type:
    | 'metric'
    | 'lookup'
    | 'filter'
    | 'extrema_lookup'
    | 'rank'
    | 'list'
    | 'aggregation_on_subset'
    | 'comparison'    // Compare two values (e.g., "sales in Jan vs Feb")
    | 'percentage'    // Calculate percentages (e.g., "what % of total is X")
    | 'trend'         // Analyze trends over time (e.g., "sales trend last 6 months")
    | 'projection';   // Forecast future values (e.g., "project next quarter")
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
  // Advanced query type specific fields
  comparison?: {
    column_a?: string;
    column_b?: string;
    value_a_filter?: FilterCondition;
    value_b_filter?: FilterCondition;
  };
  percentage?: {
    numerator_filter?: FilterCondition;
    denominator_filter?: FilterCondition;
    of_total?: boolean;
  };
  trend?: {
    date_column?: string;
    metric_column?: string;
    periods?: number;
    direction?: 'increasing' | 'decreasing' | 'stable';
  };
  projection?: {
    periods_ahead?: number;
    method?: 'linear' | 'average' | 'growth_rate';
  };
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
  preview_data?: Record<string, unknown>[];
  total_rows?: number;
  columns?: string[];
}

/** Per-table profile summary from backend profile_store */
export interface TableProfileSummary {
  name: string;
  table_type: string;
  row_count: number;
  column_count: number;
  metrics: string[];
  dimensions: string[];
  date_columns: string[];
  identifiers: string[];
  date_range: { min: string; max: string } | null;
  granularity: string;
  data_quality_score: number;
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

// Metric card data (single-value display, not chart)
export interface MetricCardData {
  value: number | string;
  is_percentage?: boolean;
  is_currency?: boolean;
  supporting_text?: string;
}

export type VisualizationType = 'bar' | 'line' | 'pie' | 'horizontal_bar' | 'metric_card';

export interface VisualizationConfig {
  type: VisualizationType;
  title: string;
  data: VisualizationDataPoint[] | MetricCardData;
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
  name_changed?: boolean;
  new_name?: string;
  is_llm_fallback?: boolean;   // True when Gemini general LLM provided the answer
  is_raw_fallback?: boolean;   // True when raw table data was shown as fallback
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

// ============================================================================
// Plug-and-Play Data Source Types
// ============================================================================

export type DataSourceType =
  | 'google_sheets'
  | 'google_drive_folder'
  | 'google_drive_file'
  | 'csv'
  | 'excel'
  | 'dropbox'
  | 'onedrive'
  | 'local';

export type DataSourceStatus =
  | 'connected'
  | 'syncing'
  | 'error'
  | 'disconnected';

export interface DataSource {
  id: string;
  type: DataSourceType;
  name: string;
  url: string;
  status: DataSourceStatus;
  lastSync?: string;
  tableCount: number;
  recordCount: number;
  error?: string;
  isAutoSync?: boolean;  // True for demo mode drive folder
  tables?: string[];
}

export interface DataSourcesResponse {
  success: boolean;
  sources: DataSource[];
  totalTables: number;
  totalRecords: number;
  demoMode: boolean;
  demoFolderUrl?: string;
}
