'use client';

import { useState, useRef, useEffect } from 'react';
import { Sparkles, Send, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface VoiceModeInputProps {
  suggestions: string[];
  onSend: (text: string) => void;
  onOpenChat: () => void;
}

export function VoiceModeInput({ suggestions, onSend, onOpenChat }: VoiceModeInputProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [displayText, setDisplayText] = useState('');
  const [isTyping, setIsTyping] = useState(true);
  const [isFocused, setIsFocused] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Typing animation for suggestions (only when not focused)
  useEffect(() => {
    if (isFocused) return;

    const currentSuggestion = suggestions[currentIndex];
    let charIndex = 0;
    let timeout: NodeJS.Timeout;

    if (isTyping) {
      const typeChar = () => {
        if (charIndex <= currentSuggestion.length) {
          setDisplayText(currentSuggestion.slice(0, charIndex));
          charIndex++;
          timeout = setTimeout(typeChar, 50);
        } else {
          timeout = setTimeout(() => setIsTyping(false), 2000);
        }
      };
      typeChar();
    } else {
      let eraseIndex = currentSuggestion.length;
      const eraseChar = () => {
        if (eraseIndex >= 0) {
          setDisplayText(currentSuggestion.slice(0, eraseIndex));
          eraseIndex--;
          timeout = setTimeout(eraseChar, 30);
        } else {
          setCurrentIndex((prev) => (prev + 1) % suggestions.length);
          setIsTyping(true);
        }
      };
      eraseChar();
    }

    return () => clearTimeout(timeout);
  }, [currentIndex, isTyping, suggestions, isFocused]);

  const handleFocus = () => {
    setIsFocused(true);
    if (!inputValue) {
      setInputValue(suggestions[currentIndex]);
    }
  };

  const handleBlur = () => {
    if (!inputValue.trim()) {
      setIsFocused(false);
      setInputValue('');
    }
  };

  const handleSend = () => {
    const textToSend = inputValue.trim() || suggestions[currentIndex];
    if (textToSend) {
      onSend(textToSend);
      setInputValue('');
      setIsFocused(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (inputValue.trim() || suggestions[currentIndex])) {
      handleSend();
    }
    if (e.key === 'Escape') {
      setInputValue('');
      setIsFocused(false);
      inputRef.current?.blur();
    }
  };

  return (
    <div className="group relative">
      <div className={cn(
        "flex items-center gap-2 sm:gap-3 h-11 sm:h-14 px-4 sm:px-6 rounded-full border backdrop-blur-xl shadow-lg shadow-black/20 transition-colors duration-300",
        isFocused
          ? "bg-zinc-800/90 border-violet-500/50"
          : "bg-zinc-900/80 border-zinc-700/50 hover:border-violet-500/30 cursor-text"
      )}
        onClick={() => {
          if (!isFocused) {
            setIsFocused(true);
            setTimeout(() => inputRef.current?.focus(), 50);
          }
        }}
      >
        <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 text-violet-400 shrink-0" />

        <div className="flex-1 overflow-hidden relative min-w-0 h-full flex items-center">
          {isFocused ? (
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onFocus={handleFocus}
              onBlur={handleBlur}
              onKeyDown={handleKeyDown}
              placeholder="Type your question..."
              className="w-full bg-transparent text-zinc-200 text-xs sm:text-sm font-medium outline-none placeholder:text-zinc-500"
              autoFocus
            />
          ) : (
            <span className="text-zinc-400 text-xs sm:text-sm font-medium block truncate w-full">
              {displayText}
              <span className="inline-block w-0.5 h-3 sm:h-4 bg-violet-400 ml-0.5 align-middle animate-pulse" />
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0 w-24 sm:w-28 justify-end h-full">
          {isFocused ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleSend();
              }}
              className="p-2 rounded-full bg-violet-500 hover:bg-violet-400 transition-colors flex-shrink-0"
            >
              <Send className="w-4 h-4 text-white" />
            </button>
          ) : (
            <>
              <span className="text-xs text-zinc-500 hidden sm:inline whitespace-nowrap">Click to type</span>
              <ChevronRight className="w-4 h-4 text-zinc-500 flex-shrink-0" />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
