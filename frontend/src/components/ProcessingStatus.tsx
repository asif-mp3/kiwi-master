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
  variant = 'chat',
  className
}: ProcessingStatusProps) {
  if (!isProcessing) return null;

  // Skeleton loading animation — mimics an incoming message bubble
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -5 }}
      transition={{ duration: 0.2 }}
      className={cn("flex justify-start w-full", className)}
    >
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-xs font-black text-white shadow-lg">
          T
        </div>

        {/* Skeleton message bubble */}
        <div className="bg-card/90 border border-border rounded-2xl rounded-tl-md px-4 py-3 shadow-sm min-w-[200px] max-w-[280px] space-y-2.5">
          {/* Skeleton lines with shimmer */}
          {[
            { width: '85%', delay: 0 },
            { width: '70%', delay: 0.1 },
            { width: '55%', delay: 0.2 },
          ].map((line, i) => (
            <motion.div
              key={i}
              className="h-3 rounded-full bg-muted/60 overflow-hidden relative"
              style={{ width: line.width }}
              initial={{ opacity: 0.4 }}
              animate={{ opacity: [0.4, 0.7, 0.4] }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                delay: line.delay,
                ease: "easeInOut"
              }}
            >
              {/* Shimmer effect */}
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-muted-foreground/10 to-transparent"
                animate={{ x: ['-100%', '100%'] }}
                transition={{
                  duration: 1.5,
                  repeat: Infinity,
                  delay: line.delay + 0.2,
                  ease: "easeInOut"
                }}
              />
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
