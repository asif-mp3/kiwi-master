'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

export type ProcessingStep =
  | 'transcribing'
  | 'translating_input'
  | 'understanding'
  | 'planning'
  | 'executing'
  | 'translating_output'
  | 'complete';

interface ProcessingStatusProps {
  isProcessing: boolean;
  isVoiceInput?: boolean;
  hasTamilInput?: boolean;
  variant?: 'voice' | 'chat';
  className?: string;
}

export function ProcessingStatus({
  isProcessing,
  isVoiceInput = false,
  hasTamilInput = false,
  variant = 'chat',
  className
}: ProcessingStatusProps) {
  if (!isProcessing) return null;

  // Simple typing indicator - three pulsing dots
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className={cn("flex justify-start w-full", className)}
    >
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-xs font-black text-white shadow-lg">
          T
        </div>

        {/* Typing bubble */}
        <div className="bg-card/90 border border-border rounded-2xl rounded-tl-md px-4 py-3 shadow-sm">
          <div className="flex items-center gap-1.5">
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="w-2 h-2 rounded-full bg-violet-400"
                animate={{
                  y: [0, -6, 0],
                  opacity: [0.4, 1, 0.4]
                }}
                transition={{
                  duration: 0.6,
                  repeat: Infinity,
                  delay: i * 0.15,
                  ease: "easeInOut"
                }}
              />
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
