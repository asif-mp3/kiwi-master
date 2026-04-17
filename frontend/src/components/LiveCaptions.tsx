'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Quote } from 'lucide-react';
import { cn } from '@/lib/utils';

export type CaptionData = { text: string; type: 'user' | 'assistant' | 'status' } | null;

interface LiveCaptionsProps {
  caption: CaptionData;
  isRecording: boolean;
  isProcessing: boolean;
  isSpeaking: boolean;
}

export function LiveCaptions({ caption, isRecording, isProcessing, isSpeaking }: LiveCaptionsProps) {
  const [displayedWords, setDisplayedWords] = useState<string[]>([]);
  const prevCaptionRef = useRef<string | null>(null);

  useEffect(() => {
    if (!caption?.text) {
      setDisplayedWords([]);
      prevCaptionRef.current = null;
      return;
    }

    const words = caption.text.split(' ');

    if (caption.text !== prevCaptionRef.current) {
      prevCaptionRef.current = caption.text;
      setDisplayedWords([]);

      let wordIdx = 0;
      const interval = setInterval(() => {
        if (wordIdx < words.length) {
          setDisplayedWords(prev => [...prev, words[wordIdx]]);
          wordIdx++;
        } else {
          clearInterval(interval);
        }
      }, 80);

      return () => clearInterval(interval);
    }
  }, [caption?.text]);

  const statusText = isRecording ? "Listening..." : isProcessing ? "Processing..." : "...";

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="hidden lg:flex flex-col items-end justify-center h-full pr-8 max-w-xs"
    >
      <AnimatePresence mode="wait">
        {(isRecording || isProcessing || isSpeaking || caption) && (
          <motion.div
            key={caption?.type || 'status'}
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="relative"
          >
            <Quote className="absolute -top-2 -left-4 w-6 h-6 text-violet-500/30 rotate-180" />
            <div className={cn(
              "relative p-4 rounded-2xl backdrop-blur-sm max-w-[280px]",
              caption?.type === 'user'
                ? "bg-violet-500/10 border border-violet-500/20"
                : caption?.type === 'assistant'
                  ? "bg-purple-500/10 border border-purple-500/20"
                  : "bg-zinc-800/50 border border-zinc-700/30"
            )}>
              <div className="flex items-center gap-2 mb-2">
                {isRecording && (
                  <>
                    <span className="w-2 h-2 rounded-full bg-violet-500 animate-pulse" />
                    <span className="text-xs text-violet-400 font-medium">You</span>
                  </>
                )}
                {isProcessing && !isRecording && !isSpeaking && (
                  <>
                    <Loader2 className="w-3 h-3 text-cyan-400 animate-spin" />
                    <span className="text-xs text-cyan-400 font-medium">Thinking</span>
                  </>
                )}
                {isSpeaking && (
                  <>
                    <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse" />
                    <span className="text-xs text-purple-400 font-medium">Thara</span>
                  </>
                )}
              </div>
              <p className={cn(
                "text-sm leading-relaxed",
                caption?.type === 'user' ? "text-violet-200" :
                  caption?.type === 'assistant' ? "text-purple-200" : "text-zinc-400"
              )}>
                {caption?.text ? (
                  <>
                    {displayedWords.map((word, idx) => (
                      <motion.span
                        key={`${idx}-${word}`}
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.15 }}
                        className="inline"
                      >
                        {word}{' '}
                      </motion.span>
                    ))}
                    {displayedWords.length < (caption.text.split(' ').length) && (
                      <motion.span
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ duration: 0.8, repeat: Infinity }}
                        className="inline-block w-1.5 h-4 bg-current align-middle ml-0.5"
                      />
                    )}
                  </>
                ) : statusText}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      {!isRecording && !isProcessing && !isSpeaking && !caption && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-right">
          <p className="text-xs text-zinc-600 mb-1">Live captions</p>
          <p className="text-[10px] text-zinc-700">appear here</p>
        </motion.div>
      )}
    </motion.div>
  );
}

interface MobileCaptionsProps {
  caption: CaptionData;
  isRecording: boolean;
  isProcessing: boolean;
  isSpeaking: boolean;
  onOpenChat: () => void;
}

export function MobileCaptions({ caption, isRecording, isProcessing, isSpeaking, onOpenChat }: MobileCaptionsProps) {
  const [displayedWords, setDisplayedWords] = useState<string[]>([]);
  const [isTruncated, setIsTruncated] = useState(false);
  const textRef = useRef<HTMLParagraphElement>(null);
  const prevCaptionRef = useRef<string | null>(null);

  useEffect(() => {
    if (!caption?.text) {
      setDisplayedWords([]);
      prevCaptionRef.current = null;
      return;
    }

    const words = caption.text.split(' ');

    if (caption.text !== prevCaptionRef.current) {
      prevCaptionRef.current = caption.text;
      setDisplayedWords([]);

      let wordIdx = 0;
      const interval = setInterval(() => {
        if (wordIdx < words.length) {
          setDisplayedWords(prev => [...prev, words[wordIdx]]);
          wordIdx++;
        } else {
          clearInterval(interval);
        }
      }, 80);

      return () => clearInterval(interval);
    }
  }, [caption?.text]);

  useEffect(() => {
    if (textRef.current) {
      setIsTruncated(textRef.current.scrollHeight > textRef.current.clientHeight);
    }
  }, [displayedWords]);

  if (!isRecording && !isProcessing && !isSpeaking && !caption) {
    return null;
  }

  return (
    <AnimatePresence mode="wait">
      {(isRecording || isProcessing || isSpeaking || caption) && (
        <motion.div
          key={caption?.type || 'status'}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="lg:hidden w-full max-w-sm mx-auto px-4 mb-4"
        >
          <button
            onClick={onOpenChat}
            className={cn(
              "w-full p-3 rounded-xl backdrop-blur-sm text-center transition-all",
              "hover:scale-[1.02] active:scale-[0.98] cursor-pointer",
              caption?.type === 'user'
                ? "bg-violet-500/10 border border-violet-500/20 hover:bg-violet-500/15"
                : caption?.type === 'assistant'
                  ? "bg-purple-500/10 border border-purple-500/20 hover:bg-purple-500/15"
                  : "bg-zinc-800/30 border border-zinc-700/20 hover:bg-zinc-800/40"
            )}
          >
            <div className="flex items-center justify-center gap-2 mb-1">
              {isRecording && <span className="w-2 h-2 rounded-full bg-violet-500 animate-pulse" />}
              {isProcessing && !isRecording && !isSpeaking && (
                <Loader2 className="w-3 h-3 text-cyan-400 animate-spin" />
              )}
              {isSpeaking && <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse" />}
              <span className={cn(
                "text-xs font-medium",
                isRecording ? "text-violet-400" :
                  isSpeaking ? "text-purple-400" :
                    isProcessing ? "text-cyan-400" : "text-zinc-500"
              )}>
                {isRecording ? "You" : isSpeaking ? "Thara" : "Processing"}
              </span>
            </div>
            <p
              ref={textRef}
              className={cn(
                "text-sm line-clamp-3",
                caption?.type === 'user' ? "text-violet-200" :
                  caption?.type === 'assistant' ? "text-purple-200" : "text-zinc-400"
              )}
            >
              {caption?.text ? (
                <>
                  {displayedWords.map((word, idx) => (
                    <motion.span
                      key={`${idx}-${word}`}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.1 }}
                      className="inline"
                    >
                      {word}{' '}
                    </motion.span>
                  ))}
                  {displayedWords.length < (caption.text.split(' ').length) && (
                    <motion.span
                      animate={{ opacity: [0.3, 1, 0.3] }}
                      transition={{ duration: 0.6, repeat: Infinity }}
                      className="inline-block w-1 h-3 bg-current align-middle ml-0.5"
                    />
                  )}
                </>
              ) : (isRecording ? "Listening..." : "Working on it...")}
            </p>
            {isTruncated && caption?.text && displayedWords.length >= caption.text.split(' ').length && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-2 text-xs text-zinc-500 flex items-center justify-center gap-1"
              >
                <span>Tap to view full response</span>
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </motion.div>
            )}
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
