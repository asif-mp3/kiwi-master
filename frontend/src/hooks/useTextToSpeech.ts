'use client';

import { useState, useCallback, useRef } from 'react';
import { api } from '@/services/api';
import { toast } from 'sonner';

export function useTextToSpeech() {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  const speak = useCallback(async (text: string) => {
    try {
      setIsSpeaking(true);
      console.log('🔊 Playing TTS for:', text.substring(0, 50) + '...');

      // Call TTS endpoint via API service
      const audioBlob = await api.textToSpeech(text);
      console.log('✅ Received audio blob:', audioBlob.size, 'bytes');

      // Clean up previous audio URL
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
      }

      // Create audio URL and play
      const audioUrl = URL.createObjectURL(audioBlob);
      audioUrlRef.current = audioUrl;
      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      audio.onended = () => {
        console.log('✅ TTS playback finished');
        setIsSpeaking(false);
        if (audioUrlRef.current) {
          URL.revokeObjectURL(audioUrlRef.current);
          audioUrlRef.current = null;
        }
      };

      audio.onerror = (e) => {
        console.error('❌ Audio playback error:', e);
        setIsSpeaking(false);
        if (audioUrlRef.current) {
          URL.revokeObjectURL(audioUrlRef.current);
          audioUrlRef.current = null;
        }
      };

      await audio.play();
      console.log('▶️ TTS playback started');

    } catch (error) {
      console.error('❌ TTS error:', error);
      setIsSpeaking(false);
      toast.error('Voice playback failed', {
        description: 'Could not play audio response'
      });
    }
  }, []);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
    setIsSpeaking(false);
  }, []);

  return {
    isSpeaking,
    speak,
    stop
  };
}
