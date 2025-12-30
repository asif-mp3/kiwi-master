/**
 * Dataset-aware type definitions for kiwi-master
 * CRITICAL: These types represent backend state only.
 */

export type DatasetState =
  | "NO_DATASET" | "LOADING" | "READY_FOR_INSPECTION" | "LOCKED_FOR_QUERY" | "ERROR";

export type LoadingStage =
  | "VALIDATING_URL" | "FETCHING_SHEET" | "DETECTING_TABLES" | "NORMALIZING_DATA"
  | "LOADING_DUCKDB" | "BUILDING_SCHEMA" | "EMBEDDING_CHROMA" | "FINALIZING" | "READY" | "ERROR";

export interface StageUpdate {
  stage: LoadingStage;
  message: string;
  error: string;
}

export interface DatasetMetadata {
  spreadsheet_name: string;
  last_sync: string;
  sheets: SheetMetadata[];
}

export interface SheetMetadata {
  sheet_name: string;
  tables: TableMetadata[];
}

export interface TableMetadata {
  table_name: string;
  row_count: number;
  column_count: number;
  columns: string[];
  source_id: string;
}

export interface QueryRequest {
  question: string;
}

export interface QueryResponse {
  answer: string;
  query_plan: Record<string, any> | null;
  result_data: any[];
  schema_context: Array<{ text: string; metadata: Record<string, any> }> | null;
  metadata: {
    source_sheet?: string;
    execution_time?: number;
    row_count?: number;
    is_greeting?: boolean;
    is_memory?: boolean;
    memory_stored?: boolean;
  };
}
