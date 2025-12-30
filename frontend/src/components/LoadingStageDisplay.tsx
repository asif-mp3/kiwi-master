/**
 * Loading Stage Display - Shows real backend execution stages
 * NO fake progress bars, NO timers, NO percentages
 */

import { motion } from "framer-motion";
import type { LoadingStage } from "@/lib/dataset-types";

interface LoadingStageDisplayProps {
  currentStage: LoadingStage;
  message?: string;
  timestamp: Date;
}

const stageDescriptions: Record<LoadingStage, string> = {
  VALIDATING_URL: "Validating Google Sheets URL",
  FETCHING_SHEET: "Fetching data from Google Sheets",
  DETECTING_TABLES: "Detecting tables within sheets",
  NORMALIZING_DATA: "Normalizing data and inferring types",
  LOADING_DUCKDB: "Loading data into analytics engine",
  BUILDING_SCHEMA: "Building schema metadata",
  EMBEDDING_CHROMA: "Generating schema embeddings",
  FINALIZING: "Finalizing dataset",
  READY: "Dataset ready",
  ERROR: "Error occurred"
};

const stageIcons: Record<LoadingStage, string> = {
  VALIDATING_URL: "🔍", FETCHING_SHEET: "📊", DETECTING_TABLES: "🔎",
  NORMALIZING_DATA: "⚙️", LOADING_DUCKDB: "💾", BUILDING_SCHEMA: "📐",
  EMBEDDING_CHROMA: "🧠", FINALIZING: "✨", READY: "✅", ERROR: "❌"
};

export function LoadingStageDisplay({ currentStage, message, timestamp }: LoadingStageDisplayProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col gap-3 p-4 rounded-lg bg-black/40 backdrop-blur-xl border border-white/10"
    >
      <div className="flex items-center gap-3">
        <motion.span key={currentStage} initial={{ scale: 0.8 }} animate={{ scale: 1 }} className="text-3xl">
          {stageIcons[currentStage]}
        </motion.span>
        <div className="flex-1">
          <div className="text-sm font-medium text-emerald-400">
            {currentStage.replace(/_/g, " ")}
          </div>
          <div className="text-xs text-white/60">
            {message || stageDescriptions[currentStage]}
          </div>
        </div>
        <div className="text-xs text-white/40 font-mono">{timestamp.toLocaleTimeString()}</div>
      </div>
      {currentStage !== "READY" && currentStage !== "ERROR" && (
        <motion.div
          className="h-1 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        />
      )}
    </motion.div>
  );
}
