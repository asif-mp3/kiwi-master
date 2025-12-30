/**
 * Audio State Context
 * Global state management for audio playback to prevent overlaps
 */

'use client';

import { createContext, useContext, useState, ReactNode } from 'react';

interface AudioStateContextType {
  currentMessageId: string | null;
  setCurrentMessageId: (id: string | null) => void;
  isPlaying: boolean;
  setIsPlaying: (playing: boolean) => void;
}

const AudioStateContext = createContext<AudioStateContextType | undefined>(undefined);

export function AudioStateProvider({ children }: { children: ReactNode }) {
  const [currentMessageId, setCurrentMessageId] = useState<string | null>(null);

  const isPlaying = currentMessageId !== null;
  const setIsPlaying = (playing: boolean) => {
    if (playing) {
      setCurrentMessageId('global_active');
    } else {
      setCurrentMessageId(null);
    }
  };

  return (
    <AudioStateContext.Provider value={{
      currentMessageId,
      setCurrentMessageId,
      isPlaying,
      setIsPlaying
    }}>
      {children}
    </AudioStateContext.Provider>
  );
}

export function useAudioState() {
  const context = useContext(AudioStateContext);
  if (!context) {
    throw new Error('useAudioState must be used within AudioStateProvider');
  }
  return context;
}
