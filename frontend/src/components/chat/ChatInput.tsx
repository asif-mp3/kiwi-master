'use client';

import { motion } from 'framer-motion';
import { Input } from '@/components/ui/input';
import { Mic, Square, Send } from 'lucide-react';

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onVoiceToggle: () => void;
  isRecording: boolean;
  disabled?: boolean;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  onVoiceToggle,
  isRecording,
  disabled = false
}: ChatInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && value.trim() && !disabled) {
      onSend();
    }
  };

  return (
    <div className="absolute bottom-6 left-0 right-0 px-6 pointer-events-none">
      <div className="max-w-3xl mx-auto pointer-events-auto">
        <div className="flex items-center gap-2 p-2 rounded-2xl glass border border-border bg-card/80 backdrop-blur-xl">
          <Input
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            className="flex-1 bg-transparent border-0 focus-visible:ring-0 focus-visible:ring-offset-0 text-foreground placeholder:text-muted-foreground"
            disabled={disabled}
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onVoiceToggle}
            disabled={disabled}
            className={`w-10 h-10 rounded-xl transition-all duration-300 flex items-center justify-center ${isRecording
              ? 'bg-violet-500 shadow-[0_0_30px_rgba(139,92,246,0.5)]'
              : 'bg-secondary border border-border hover:border-primary/50'
              }`}
          >
            {isRecording ? (
              <Square className="w-5 h-5 text-white fill-current" />
            ) : (
              <Mic className="w-5 h-5 text-muted-foreground" />
            )}
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onSend}
            disabled={!value.trim() || disabled}
            className={`w-10 h-10 rounded-xl transition-all duration-300 flex items-center justify-center ${value.trim() && !disabled
              ? 'bg-primary hover:bg-primary/90 shadow-[0_0_20px_rgba(var(--primary),0.3)]'
              : 'bg-secondary border border-border opacity-50 cursor-not-allowed'
              }`}
          >
            <Send className="w-5 h-5 text-white" />
          </motion.button>
        </div>
      </div>
    </div>
  );
}
