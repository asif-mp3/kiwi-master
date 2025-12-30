/**
 * LoadingProgress Component
 * Stage-based progress visualization with real-time backend updates
 */

import { motion } from "framer-motion";
import type { LoadingStage } from "@/lib/dataset-types";

export interface LoadingStageConfig {
  stage: LoadingStage;
  label: string;
  completed: boolean;
}

interface LoadingProgressProps {
  currentStage: LoadingStage;
  stages: LoadingStageConfig[];
}

export function LoadingProgress({ currentStage, stages }: LoadingProgressProps) {
  return (
    <div className="space-y-2">
      {stages.map((stage, index) => {
        const isCurrent = stage.stage === currentStage;
        const isPending = !stage.completed && !isCurrent;

        return (
          <motion.div
            key={stage.stage}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className={`flex items-center gap-3 p-3 rounded-lg border ${stage.completed
                ? 'bg-emerald-500/10 border-emerald-500/30'
                : isCurrent
                  ? 'bg-blue-500/10 border-blue-500/30'
                  : 'bg-white/5 border-white/10'
              }`}
          >
            {/* Icon */}
            <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center">
              {stage.completed ? (
                <div className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              ) : isCurrent ? (
                <motion.div
                  className="w-5 h-5 rounded-full border-2 border-blue-500 border-t-transparent"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                />
              ) : (
                <div className="w-5 h-5 rounded-full border-2 border-white/20" />
              )}
            </div>

            {/* Label */}
            <div className={`flex-1 text-sm font-medium ${stage.completed
                ? 'text-emerald-400'
                : isCurrent
                  ? 'text-blue-400'
                  : 'text-white/40'
              }`}>
              {stage.label}
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
