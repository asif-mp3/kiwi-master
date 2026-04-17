'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, CheckCircle, AlertCircle, Database } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface LoadingStatus {
  phase: 'idle' | 'connecting' | 'fetching' | 'profiling' | 'ready' | 'error';
  message: string;
  progress: number;
  tables_found: number;
  tables_profiled: number;
  total_tables: number;
  complete: boolean;
  error: string | null;
}

interface DataLoadingOverlayProps {
  status: LoadingStatus;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export function DataLoadingOverlay({ status, onRetry, onDismiss }: DataLoadingOverlayProps) {
  const isVisible = status.phase !== 'idle' && status.phase !== 'ready';
  const isReady = status.phase === 'ready';
  const isError = status.phase === 'error';

  return (
    <AnimatePresence>
      {(isVisible || isReady) && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
          className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-[90vw] max-w-md"
        >
          <div className="rounded-2xl border border-border bg-card/95 backdrop-blur-xl shadow-2xl shadow-black/20 p-5">
            {/* Header */}
            <div className="flex items-center gap-3 mb-3">
              {isError ? (
                <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center">
                  <AlertCircle className="w-5 h-5 text-red-500" />
                </div>
              ) : isReady ? (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="w-10 h-10 rounded-xl bg-green-500/10 flex items-center justify-center"
                >
                  <CheckCircle className="w-5 h-5 text-green-500" />
                </motion.div>
              ) : (
                <div className="w-10 h-10 rounded-xl bg-violet-500/10 flex items-center justify-center">
                  <Loader2 className="w-5 h-5 text-violet-500 animate-spin" />
                </div>
              )}
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-foreground truncate">
                  {isError ? 'Loading failed' : isReady ? 'Data ready!' : 'Setting up your data...'}
                </h3>
                <p className="text-xs text-muted-foreground truncate">{status.message}</p>
              </div>
            </div>

            {/* Progress Bar */}
            {!isError && (
              <div className="mb-3">
                <div className="h-2 rounded-full bg-muted overflow-hidden">
                  <motion.div
                    className={`h-full rounded-full ${isReady ? 'bg-green-500' : 'bg-violet-500'}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${status.progress}%` }}
                    transition={{ duration: 0.5, ease: 'easeOut' }}
                  />
                </div>
                {status.phase === 'profiling' && status.total_tables > 0 && (
                  <div className="flex items-center justify-between mt-1.5">
                    <span className="text-[10px] text-muted-foreground">
                      Analyzing table {status.tables_profiled + 1} of {status.total_tables}
                    </span>
                    <span className="text-[10px] font-medium text-violet-400">
                      {status.progress}%
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Stats when ready */}
            {isReady && status.total_tables > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="flex items-center gap-2 mb-3"
              >
                <Database className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">
                  {status.total_tables} tables loaded
                </span>
              </motion.div>
            )}

            {/* Error actions */}
            {isError && (
              <div className="flex gap-2 mt-2">
                {onRetry && (
                  <Button size="sm" variant="outline" onClick={onRetry} className="text-xs h-8">
                    Retry
                  </Button>
                )}
              </div>
            )}

            {/* Auto-dismiss for ready state */}
            {isReady && onDismiss && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.5 }}
              >
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={onDismiss}
                  className="text-xs h-7 text-muted-foreground w-full"
                >
                  Dismiss
                </Button>
              </motion.div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
