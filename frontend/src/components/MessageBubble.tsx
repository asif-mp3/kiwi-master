'use client';

import { motion } from 'framer-motion';
import { Message } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Play, Copy, Check, Volume2, Square } from 'lucide-react';
import { useState } from 'react';
import { audioPlayer } from '@/lib/audio-player';
import { toast } from 'sonner';
import { useAudioState } from '@/lib/audio-state';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isAssistant = message.role === 'assistant';
  const isSystem = message.role === 'system';
  const [copied, setCopied] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  // Use shared audio state so stop button works for auto-play too
  const { isPlaying, setIsPlaying, currentMessageId, setCurrentMessageId } = useAudioState();

  // Check if THIS message is currently playing
  const isThisMessagePlaying = isPlaying && currentMessageId === message.id;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      toast.success("Copied!", {
        description: "Message copied to clipboard",
      });
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      toast.error("Failed to copy", {
        description: "Could not copy message to clipboard",
      });
    }
  };

  const handlePlay = async () => {
    try {
      setIsPlaying(true);
      setCurrentMessageId(message.id);
      toast.info("Playing audio...", {
        description: "Converting text to speech",
        id: "playback-start" // Id avoids duplicates
      });

      // Play the message content as audio
      await audioPlayer.playText(message.content);

      // Only show complete if we are still the current message (meaning not interrupted by another play)
      // We can't easily know if it was stopped manually vs finished naturally here without more state,
      // but the side effect of 'stop' clearing currentMessageId helps.
      setIsPlaying(false);
      setCurrentMessageId(null);

      // Note: We don't show "Playback complete" here because if it was stopped manually,
      // handleStop handles the UI update. If it finished naturally, we could show it,
      // but it's often redundant.
    } catch (error) {
      setIsPlaying(false);
      setCurrentMessageId(null);
      // Don't show error if it was just a manual stop/interruption which might look like an error
      if (error instanceof Error && error.message !== 'Audio playback failed') {
        toast.error("Playback failed", {
          description: error.message,
        });
      }
    }
  };

  const handleStop = () => {
    // Stop the actual audio hardware
    audioPlayer.stop();

    // Update local state immediately
    setIsPlaying(false);
    setCurrentMessageId(null);

    toast.info("Playback stopped", {
      id: "playback-stop"
    });
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
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-green-500 to-teal-500 flex items-center justify-center text-[10px] font-black text-white">
              K
            </div>
            <span className="text-xs font-semibold text-zinc-400">Kiwi</span>
          </div>
        )}

        <motion.div
          animate={{
            scale: isHovered ? 1.01 : 1,
            boxShadow: isHovered
              ? isAssistant
                ? '0 10px 40px rgba(34, 197, 94, 0.1)'
                : '0 10px 40px rgba(0, 0, 0, 0.3)'
              : '0 4px 20px rgba(0, 0, 0, 0.1)'
          }}
          transition={{ duration: 0.2 }}
          className={cn(
            "px-5 py-4 rounded-2xl text-[15px] leading-relaxed transition-all duration-300",
            isAssistant
              ? "bg-card/80 backdrop-blur-xl text-card-foreground border border-border rounded-tl-md"
              : "bg-gradient-to-br from-green-600 to-green-700 text-white shadow-lg rounded-tr-md"
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
            isAssistant ? "text-muted-foreground" : "text-green-100"
          )}>
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </motion.div>

        {/* Action Buttons */}
        {isAssistant && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{
              opacity: (isHovered || isThisMessagePlaying) ? 1 : 0,
              y: (isHovered || isThisMessagePlaying) ? 0 : -10
            }}
            transition={{ duration: 0.2 }}
            className="mt-2 flex items-center gap-2"
          >
            {/* Play/Stop Button - Click any stop button to halt playback */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={(e) => {
                e.stopPropagation();
                isPlaying ? handleStop() : handlePlay();
              }}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-semibold uppercase tracking-wider transition-all",
                isPlaying
                  ? "bg-red-500/20 text-red-400 hover:bg-red-500/30"
                  : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              {isPlaying ? (
                <>
                  <Square className="w-3 h-3 fill-current" />
                  Stop
                </>
              ) : (
                <>
                  <Volume2 className="w-3 h-3" />
                  Play
                </>
              )}
            </motion.button>

            {/* Copy Button */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleCopy}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-semibold uppercase tracking-wider transition-all",
                copied
                  ? "bg-green-500/20 text-green-400"
                  : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  Copy
                </>
              )}
            </motion.button>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
