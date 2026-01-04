'use client';

import { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';
import { Message } from '@/lib/types';
import { MessageBubble } from '../MessageBubble';

interface MessageListProps {
  messages: Message[];
  isSpeaking: boolean;
  onPlayMessage: (text: string) => void;
}

export function MessageList({ messages, isSpeaking, onPlayMessage }: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto space-y-6 pb-32 hide-scrollbar"
    >
      {messages.length === 0 ? (
        <div className="h-64 flex flex-col items-center justify-center opacity-40">
          <Sparkles className="w-12 h-12 mb-4 text-violet-500/50" />
          <p className="text-sm font-medium">Start a conversation with Thara</p>
          <p className="text-xs text-zinc-600 mt-1">Use voice or type to begin</p>
        </div>
      ) : (
        messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} onPlay={onPlayMessage} />
        ))
      )}
      {isSpeaking && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 p-4 rounded-2xl bg-violet-500/5 border border-violet-500/10 max-w-[80%]"
        >
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                animate={{ height: [4, 16, 4] }}
                transition={{ duration: 0.5, repeat: Infinity, delay: i * 0.1 }}
                className="w-1 bg-violet-400 rounded-full"
              />
            ))}
          </div>
          <span className="text-xs font-medium text-violet-400">Thara is typing...</span>
        </motion.div>
      )}
    </div>
  );
}
