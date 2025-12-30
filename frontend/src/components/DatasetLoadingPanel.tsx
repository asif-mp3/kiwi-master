/**
 * Dataset Loading Panel
 * 
 * CRITICAL: This panel displays REAL backend execution stages only.
 * - No fake progress bars
 * - No percentage completion
 * - No time estimation
 * - No simulated stages
 * 
 * Updates ONLY when backend emits a stage via SSE.
 */

'use client';

import { motion } from "framer-motion";
import type { LoadingStage } from "@/lib/dataset-types";

interface DatasetLoadingPanelProps {
  sheetUrl: string;
  currentStage: LoadingStage;
  stageMessage?: string;
}

// Stage descriptions - FACTUAL ONLY, no analysis/computation language
const STAGE_DESCRIPTIONS: Record<LoadingStage, string> = {
  VALIDATING_URL: "Validating Google Sheets access and permissions.",
  FETCHING_SHEET: "Fetching raw sheet data from Google Sheets.",
  DETECTING_TABLES: "Detecting structured tables within the sheet.",
  NORMALIZING_DATA: "Normalizing headers and table structure.",
  LOADING_DUCKDB: "Loading structured data into the analytics engine.",
  BUILDING_SCHEMA: "Building dataset schema for accurate querying.",
  EMBEDDING_CHROMA: "Indexing schema semantics for query understanding.",
  FINALIZING: "Finalizing dataset preparation.",
  READY: "Dataset is ready for inspection.",
  ERROR: "Dataset loading failed."
};

// Ordered stages for visual progress
const ORDERED_STAGES: LoadingStage[] = [
  "VALIDATING_URL",
  "FETCHING_SHEET",
  "DETECTING_TABLES",
  "NORMALIZING_DATA",
  "LOADING_DUCKDB",
  "BUILDING_SCHEMA",
  "EMBEDDING_CHROMA",
  "FINALIZING",
  "READY"
];

export function DatasetLoadingPanel({
  sheetUrl,
  currentStage,
  stageMessage
}: DatasetLoadingPanelProps) {
  const currentStageIndex = ORDERED_STAGES.indexOf(currentStage);

  // Truncate URL for display
  const truncatedUrl = sheetUrl.length > 60
    ? sheetUrl.substring(0, 57) + "..."
    : sheetUrl;

  return (
    <div className="fixed inset-0 bg-gradient-to-br from-black via-gray-900 to-black flex items-center justify-center z-50">
      <div className="max-w-2xl w-full px-6 space-y-8">

        {/* HEADER SECTION - Locked Dataset Identity */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6"
        >
          <div className="flex items-start gap-4">
            {/* Lock Icon */}
            <div className="flex-shrink-0 w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
              <svg className="w-6 h-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>

            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-emerald-400 mb-1">
                Preparing dataset for analysis
              </div>
              <div className="text-xs text-white/60 font-mono truncate">
                {truncatedUrl}
              </div>
            </div>
          </div>
        </motion.div>

        {/* PRIMARY STATUS MESSAGE - Single, Clear, Stage-Driven */}
        <motion.div
          key={currentStage}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="text-center space-y-2"
        >
          <div className="text-2xl font-medium text-white">
            {stageMessage || STAGE_DESCRIPTIONS[currentStage]}
          </div>
          <div className="text-sm text-white/40">
            No analysis or computation has started yet.
          </div>
        </motion.div>

        {/* VISUAL PROGRESS - Stage-Based, No Percentages */}
        <div className="space-y-3">
          {ORDERED_STAGES.map((stage, index) => {
            const isCompleted = index < currentStageIndex;
            const isCurrent = stage === currentStage;
            const isPending = index > currentStageIndex;

            return (
              <motion.div
                key={stage}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className={`flex items-center gap-4 p-4 rounded-xl border transition-all ${isCompleted
                    ? 'bg-emerald-500/5 border-emerald-500/20'
                    : isCurrent
                      ? 'bg-blue-500/10 border-blue-500/30 shadow-lg shadow-blue-500/10'
                      : 'bg-white/5 border-white/10'
                  }`}
              >
                {/* Stage Indicator */}
                <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center">
                  {isCompleted ? (
                    // Completed - Checkmark
                    <div className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center">
                      <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  ) : isCurrent ? (
                    // Current - Pulsing Dot (NOT a spinner)
                    <motion.div
                      animate={{
                        scale: [1, 1.2, 1],
                        opacity: [0.5, 1, 0.5]
                      }}
                      transition={{
                        duration: 2,
                        repeat: Infinity,
                        ease: "easeInOut"
                      }}
                      className="w-4 h-4 rounded-full bg-blue-400"
                    />
                  ) : (
                    // Pending - Empty Circle
                    <div className="w-6 h-6 rounded-full border-2 border-white/20" />
                  )}
                </div>

                {/* Stage Label */}
                <div className={`flex-1 text-sm font-medium ${isCompleted
                    ? 'text-emerald-400'
                    : isCurrent
                      ? 'text-blue-400'
                      : 'text-white/30'
                  }`}>
                  {stage.replace(/_/g, ' ')}
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Footer Note - Reinforces Truth */}
        <div className="text-center text-xs text-white/30">
          Progress reflects real execution stages from the backend.
          <br />
          No simulation or estimation is used.
        </div>
      </div>
    </div>
  );
}
