'use client';

import { motion } from 'framer-motion';
import { Message } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Play, Copy, Check, Volume2, Database } from 'lucide-react';
import { useState } from 'react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { QueryPlanViewer } from './QueryPlanViewer';

interface MessageBubbleProps {
  message: Message;
  onPlay?: (text: string) => void;
}

export function MessageBubble({ message, onPlay }: MessageBubbleProps) {
  const isAssistant = message.role === 'assistant';
  const isSystem = message.role === 'system';
  const [copied, setCopied] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isSystem) {
    return (
      <div className="flex justify-center w-full my-6">
        <span className="text-[10px] uppercase tracking-[0.3em] text-zinc-600 font-bold">
          {message.content}
        </span>
      </div>
    );
  }

  const hasTamil = /[\u0B80-\u0BFF]/.test(message.content);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      className={cn(
        "flex w-full group",
        isAssistant ? "justify-start" : "justify-end"
      )}
    >
      <div
        className={cn(
          "max-w-[85%] md:max-w-[75%] relative",
          isAssistant ? "items-start" : "items-end flex flex-col"
        )}
      >
        {/* Avatar for Assistant */}
        {isAssistant && (
          <div className="flex items-center gap-3 mb-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center text-[10px] font-black text-white">
              T
            </div>
            <span className="text-xs font-semibold text-zinc-400">Thara</span>
          </div>
        )}

        <motion.div
          animate={{
            scale: isHovered ? 1.01 : 1,
            boxShadow: isHovered
              ? isAssistant
                ? '0 10px 40px rgba(139, 92, 246, 0.1)'
                : '0 10px 40px rgba(0, 0, 0, 0.3)'
              : '0 4px 20px rgba(0, 0, 0, 0.1)'
          }}
          transition={{ duration: 0.2 }}
          className={cn(
            "px-3 py-3 sm:px-5 sm:py-4 rounded-xl sm:rounded-2xl text-sm sm:text-[15px] leading-relaxed transition-all duration-300",
            isAssistant
              ? "bg-card/80 backdrop-blur-xl text-card-foreground border border-border rounded-tl-md"
              : "bg-gradient-to-br from-violet-600 to-violet-700 text-white shadow-lg rounded-tr-md"
          )}
        >
          <div className={cn(
            "whitespace-pre-wrap font-medium",
            hasTamil ? "leading-[1.9]" : "leading-relaxed"
          )}>
            {message.content}
          </div>

          <div className={cn(
            "mt-2 text-[10px] font-medium tracking-wide opacity-50",
            isAssistant ? "text-muted-foreground" : "text-violet-100"
          )}>
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </motion.div>

        {/* Action Buttons */}
        {isAssistant && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="mt-1.5 sm:mt-2 flex items-center gap-1 sm:gap-2 flex-wrap"
          >
            {[
              { icon: Volume2, label: 'Play', ariaLabel: 'Play message audio', onClick: () => onPlay?.(message.content) },
              { icon: copied ? Check : Copy, label: copied ? 'Copied!' : 'Copy', ariaLabel: 'Copy message', onClick: handleCopy },
            ].map((action, i) => (
              <motion.button
                key={i}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={action.onClick}
                aria-label={action.ariaLabel}
                className={cn(
                  "flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1 sm:py-1.5 rounded-md sm:rounded-lg text-[9px] sm:text-[10px] font-semibold uppercase tracking-wider transition-all",
                  copied && action.label === 'Copied!'
                    ? "bg-green-500/20 text-green-400"
                    : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <action.icon className="w-3 h-3" />
                <span className="hidden sm:inline">{action.label}</span>
              </motion.button>
            ))}

            {message.metadata?.plan && (
              <Popover>
                <PopoverTrigger asChild>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    aria-label="View query plan"
                    className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-3 py-1 sm:py-1.5 rounded-md sm:rounded-lg text-[9px] sm:text-[10px] font-semibold uppercase tracking-wider transition-all bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
                  >
                    <Database className="w-3 h-3" />
                    <span className="hidden sm:inline">Query Plan</span>
                  </motion.button>
                </PopoverTrigger>
                <PopoverContent className="w-[calc(100vw-2rem)] sm:w-96 max-w-96 p-3 sm:p-4 bg-zinc-950/95 backdrop-blur-xl border border-zinc-800 shadow-2xl rounded-xl">
                  <QueryPlanViewer plan={message.metadata.plan} />
                </PopoverContent>
              </Popover>
            )}
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
