'use client';

import { useState, useRef } from 'react';
import { Sparkles, Send } from 'lucide-react';
import { cn } from '@/lib/utils';

interface VoiceModeInputProps {
  suggestions: string[];
  onSend: (text: string) => void;
  onOpenChat: () => void;
}

export function VoiceModeInput({ suggestions, onSend, onOpenChat }: VoiceModeInputProps) {
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    const textToSend = inputValue.trim();
    if (textToSend) {
      onSend(textToSend);
      setInputValue('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      handleSend();
    }
    if (e.key === 'Escape') {
      setInputValue('');
      inputRef.current?.blur();
    }
  };

  return (
    <div className="group relative">
      <div className={cn(
        "flex items-center gap-2 sm:gap-3 h-11 sm:h-14 px-3 sm:px-6 rounded-full border backdrop-blur-xl shadow-lg shadow-black/20 transition-colors duration-300 bg-zinc-900/80 border-zinc-700/50 focus-within:border-violet-500/50"
      )}
      >
        <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 text-violet-400 shrink-0" />

        <div className="flex-1 overflow-hidden relative min-w-0 h-full flex items-center">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your question..."
            className="w-full bg-transparent text-zinc-200 text-xs sm:text-sm font-medium outline-none placeholder:text-zinc-500"
          />
        </div>

        <div className="flex items-center shrink-0 h-full">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleSend();
            }}
            disabled={!inputValue.trim()}
            className={cn(
              "p-2 rounded-full transition-colors flex-shrink-0",
              inputValue.trim()
                ? "bg-violet-500 hover:bg-violet-400"
                : "bg-zinc-700/60 cursor-not-allowed"
            )}
          >
            <Send className="w-4 h-4 text-white" />
          </button>
        </div>
      </div>
    </div>
  );
}
