'use client';

import { useState, useCallback, useRef } from 'react';
import { api } from '@/services/api';
import { toast } from 'sonner';
import { VOICE_RECORDING_TIMEOUT } from '@/lib/constants';

interface UseVoiceRecordingOptions {
  onTranscription?: (text: string) => void;
  onError?: (error: Error) => void;
}

export function useVoiceRecording(options: UseVoiceRecordingOptions = {}) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const recorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      const chunks: Blob[] = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      recorder.onstop = async () => {
        console.log('🎤 Recording stopped, processing...');

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());

        // Create audio blob from chunks
        const audioBlob = new Blob(chunks, { type: 'audio/webm;codecs=opus' });
        console.log('📦 Audio blob size:', audioBlob.size, 'bytes');

        try {
          setIsProcessing(true);
          console.log('📤 Sending audio for transcription...');
          const text = await api.transcribeAudio(audioBlob);
          console.log('✅ Transcribed text:', text);

          if (!text || text.trim() === '') {
            console.warn('⚠️ Empty transcription result');
            toast.error("No speech detected", { description: "Please try speaking again." });
            return;
          }

          options.onTranscription?.(text);
        } catch (err) {
          console.error('❌ Voice processing error:', err);
          const error = err instanceof Error ? err : new Error('Unknown error');
          options.onError?.(error);
          toast.error("Voice processing failed", {
            description: error.message
          });
        } finally {
          setIsProcessing(false);
        }
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
      console.log('🔴 Recording started...');

      // Auto-stop after timeout
      setTimeout(() => {
        if (recorder.state === 'recording') {
          console.log('⏱️ Auto-stopping after timeout...');
          stopRecording();
        }
      }, VOICE_RECORDING_TIMEOUT);

    } catch (err) {
      console.error('❌ Microphone access error:', err);
      toast.error("Microphone access denied", {
        description: "Please allow microphone access to use voice input."
      });
    }
  }, [options]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      console.log('🛑 Manually stopping recording...');
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  }, []);

  const toggleRecording = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  return {
    isRecording,
    isProcessing,
    startRecording,
    stopRecording,
    toggleRecording
  };
}
