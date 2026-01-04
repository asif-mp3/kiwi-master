'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Send, StopCircle, Paperclip } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

interface ChatInputProps {
  onSendMessage: (content: string) => void;
  onVoiceStart: () => void;
  onVoiceStop: () => void;
  isRecording: boolean;
}

export function ChatInput({ onSendMessage, onVoiceStart, onVoiceStop, isRecording }: ChatInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (input.trim()) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'inherit';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  return (
    <div className="relative px-4 pb-6 pt-2 bg-zinc-50/80 dark:bg-zinc-950/80 backdrop-blur-xl border-t border-zinc-200 dark:border-zinc-800">
      <div className="max-w-3xl mx-auto relative flex items-end gap-3">
        <div className="relative flex-1 group">
          <Textarea
            ref={textareaRef}
            rows={1}
            placeholder={isRecording ? "Listening..." : "Message your assistant..."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="min-h-[52px] max-h-40 pr-12 pl-4 py-3 bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 rounded-2xl resize-none shadow-sm transition-all focus-visible:ring-1 focus-visible:ring-zinc-300 dark:focus-visible:ring-zinc-700 focus-visible:border-transparent"
            disabled={isRecording}
          />
          <div className="absolute right-2 bottom-2">
            <Button
              size="icon"
              variant="ghost"
              className="h-9 w-9 text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 rounded-xl"
            >
              <Paperclip className="w-5 h-5" />
            </Button>
          </div>
        </div>

        <div className="flex items-center gap-2 mb-[2px]">
          <AnimatePresence mode="wait">
            {input.trim() ? (
              <motion.div
                key="send"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
              >
                <Button
                  onClick={handleSend}
                  size="icon"
                  className="h-12 w-12 rounded-2xl bg-zinc-900 dark:bg-zinc-100 text-zinc-50 dark:text-zinc-900 shadow-lg shadow-zinc-200/50 dark:shadow-black/50"
                >
                  <Send className="w-5 h-5" />
                </Button>
              </motion.div>
            ) : (
              <motion.div
                key="mic"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.8, opacity: 0 }}
              >
                <Button
                  onClick={isRecording ? onVoiceStop : onVoiceStart}
                  size="icon"
                  className={`h-12 w-12 rounded-2xl transition-all duration-500 shadow-lg ${
                    isRecording
                      ? 'bg-red-500 text-white shadow-red-200/50 ring-4 ring-red-500/20'
                      : 'bg-zinc-900 dark:bg-zinc-100 text-zinc-50 dark:text-zinc-900 shadow-zinc-200/50 dark:shadow-black/50 hover:scale-105'
                  }`}
                >
                  {isRecording ? (
                    <StopCircle className="w-6 h-6 animate-pulse" />
                  ) : (
                    <Mic className="w-6 h-6" />
                  )}
                </Button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
      
      {isRecording && (
        <div className="absolute top-0 left-0 w-full -translate-y-full px-4 pb-2 flex justify-center">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="bg-white dark:bg-zinc-900 px-6 py-2 rounded-full shadow-xl border border-zinc-100 dark:border-zinc-800 flex items-center gap-4"
          >
            <div className="flex gap-1 items-center">
              {[1, 2, 3, 4, 5, 6, 7].map((i) => (
                <motion.div
                  key={i}
                  animate={{ height: [8, 20, 8] }}
                  transition={{
                    repeat: Infinity,
                    duration: 0.5,
                    delay: i * 0.05,
                  }}
                  className="w-1 bg-red-500 rounded-full"
                />
              ))}
            </div>
            <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-widest">
              Recording Audio
            </span>
          </motion.div>
        </div>
      )}
    </div>
  );
}
