'use client';

import { useState, useRef, useEffect } from 'react';
import { toast } from 'sonner';
import { api } from '@/services/api';
import {
  VOICE_RECORDING_TIMEOUT,
  VOICE_MODE_TIMEOUT,
  NO_SPEECH_CANCEL_TIMEOUT,
  VAD_SILENCE_THRESHOLD,
  VAD_SILENCE_DURATION,
  VAD_MIN_SPEECH_DURATION,
  VAD_CHECK_INTERVAL
} from '@/lib/constants';

// ============================================================================
// Types
// ============================================================================

export interface UseVoiceOptions {
  isConnectionVerified: boolean;
  activeChat: { id: string } | null;
  isInChatView: boolean;
  addMessage: (content: string, role: 'user' | 'assistant', metadata?: Record<string, unknown>) => void;
  sendMessage: (content: string, shouldPlayTTS: boolean, isVoiceInput: boolean) => Promise<void>;
  setLiveCaption: (caption: { text: string; type: 'user' | 'assistant' | 'status' } | null) => void;
  setExpandedVoiceSection: (section: 'plan' | 'data' | 'schema' | null) => void;
  setIsProcessingQuery: (v: boolean) => void;
  setIsCurrentInputVoice: (v: boolean) => void;
  setHasTamilInput: (v: boolean) => void;
}

// ============================================================================
// Constants & Helpers
// ============================================================================

const CONCLUDING_PHRASES = [
  'thank you', 'thanks', 'thank you so much', 'thanks a lot', 'many thanks',
  'okay', 'ok', 'alright', 'all right', 'got it', 'understood',
  'bye', 'goodbye', 'good bye', 'see you', 'take care',
  "that's all", "that's it", "i'm done", 'im done', 'done', 'finished',
  'nothing else', 'no more questions', 'that will be all',
  'நன்றி', 'போய் வருகிறேன்', 'சரி'
];

const FAREWELL_RESPONSES = [
  "You're welcome! Feel free to ask anytime. Goodbye!",
  "Happy to help! Have a great day!",
  "Glad I could assist! Take care!",
  "Anytime! See you next time!",
  "My pleasure! Don't hesitate to come back if you need anything.",
  "Thank you for using Thara! Goodbye!"
];

function isConcludingPhrase(text: string): boolean {
  const normalized = text.toLowerCase().trim();
  return CONCLUDING_PHRASES.some(phrase =>
    normalized === phrase ||
    normalized.startsWith(phrase + ' ') ||
    normalized.endsWith(' ' + phrase)
  );
}

function getFarewellResponse(): string {
  return FAREWELL_RESPONSES[Math.floor(Math.random() * FAREWELL_RESPONSES.length)];
}

// ============================================================================
// Hook
// ============================================================================

export function useVoice(options: UseVoiceOptions) {
  // Destructure for effect dependencies (reactive)
  const { isInChatView } = options;

  // Store full options in ref for async callbacks (always latest)
  const optionsRef = useRef(options);
  useEffect(() => { optionsRef.current = options; });

  // ===== State =====
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessingVoice, setIsProcessingVoice] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [isVoiceEnabledInChat, setIsVoiceEnabledInChat] = useState(false);
  const [isAlwaysOnMode, setIsAlwaysOnMode] = useState(false);
  const [isFullscreenVoice, setIsFullscreenVoice] = useState(false);
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);
  const [voiceLatencyMs, setVoiceLatencyMs] = useState<number | null>(null);

  // ===== Refs =====
  const vadStopTimestampRef = useRef<number | null>(null);
  const shouldResumeRecording = useRef(false);
  const isAlwaysOnModeRef = useRef(false);
  const userAbortedRef = useRef(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const voiceModeTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const recordingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const vadIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const silenceStartRef = useRef<number | null>(null);
  const speechStartRef = useRef<number | null>(null);
  const isTogglingVoiceRef = useRef(false);
  const activeRecordingRef = useRef(false);
  const noSpeechTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const hadSpeechRef = useRef(false);

  // ===== Effects =====

  // Keep ref in sync with state
  useEffect(() => { isAlwaysOnModeRef.current = isAlwaysOnMode; }, [isAlwaysOnMode]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (voiceModeTimeoutRef.current) clearTimeout(voiceModeTimeoutRef.current);
      if (recordingTimeoutRef.current) clearTimeout(recordingTimeoutRef.current);
      if (noSpeechTimeoutRef.current) clearTimeout(noSpeechTimeoutRef.current);
      if (vadIntervalRef.current) clearInterval(vadIntervalRef.current);
      if (audioContextRef.current) audioContextRef.current.close();
    };
  }, []);

  // Stop recording when voice is disabled in chat mode
  useEffect(() => {
    if (!isVoiceEnabledInChat && isRecording && isInChatView) {
      if (mediaRecorder && mediaRecorder.state === 'recording') {
        userAbortedRef.current = true;
        mediaRecorder.stop();
      }
      setIsRecording(false);
    }
  }, [isVoiceEnabledInChat, isRecording, isInChatView, mediaRecorder]);

  // ===== Internal Helpers =====

  const stopVAD = () => {
    if (vadIntervalRef.current) {
      clearInterval(vadIntervalRef.current);
      vadIntervalRef.current = null;
    }
    silenceStartRef.current = null;
    speechStartRef.current = null;
  };

  const setupVAD = (stream: MediaStream, recorder: MediaRecorder) => {
    try {
      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.3;
      source.connect(analyser);
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      speechStartRef.current = Date.now();
      silenceStartRef.current = null;

      vadIntervalRef.current = setInterval(() => {
        if (!analyserRef.current || recorder.state !== 'recording') {
          stopVAD();
          return;
        }

        analyser.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
        const now = Date.now();
        const speechDuration = now - (speechStartRef.current || now);

        if (speechDuration < VAD_MIN_SPEECH_DURATION) return;

        if (average < VAD_SILENCE_THRESHOLD) {
          if (!silenceStartRef.current) {
            silenceStartRef.current = now;
          } else if (now - silenceStartRef.current > VAD_SILENCE_DURATION) {
            stopVAD();
            if (recorder.state === 'recording') {
              vadStopTimestampRef.current = performance.now();
              recorder.stop();
              setIsRecording(false);
            }
          }
        } else {
          silenceStartRef.current = null;
        }
      }, VAD_CHECK_INTERVAL);
    } catch (vadError) {
      // Error handled silently
    }
  };

  const setRecordingTimeout = (recorder: MediaRecorder) => {
    if (recordingTimeoutRef.current) clearTimeout(recordingTimeoutRef.current);
    recordingTimeoutRef.current = setTimeout(() => {
      stopVAD();
      if (recorder.state === 'recording') {
        recorder.stop();
        setIsRecording(false);
      }
      recordingTimeoutRef.current = null;
    }, VOICE_RECORDING_TIMEOUT);
  };

  /** Handle concluding/farewell phrases. Returns true if farewell was detected. */
  const handleFarewell = async (text: string): Promise<boolean> => {
    if (!isConcludingPhrase(text)) return false;

    const opts = optionsRef.current;
    opts.addMessage(text, 'user');
    const farewellMsg = getFarewellResponse();
    opts.addMessage(farewellMsg, 'assistant');
    opts.setLiveCaption({ text: farewellMsg, type: 'assistant' });

    setIsVoiceMode(true);
    await playTextToSpeech(farewellMsg);

    setIsAlwaysOnMode(false);
    shouldResumeRecording.current = false;
    setIsFullscreenVoice(false);
    setIsProcessingVoice(false);

    setTimeout(() => opts.setLiveCaption(null), 3000);
    toast.success("Conversation ended", { description: "Tap mic to start again" });
    return true;
  };

  // ===== TTS Playback =====

  const playTextToSpeech = async (text: string, messageId?: string) => {
    try {
      // Stop any currently playing audio
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
        audioRef.current = null;
      }

      setSpeakingMessageId(messageId || null);

      // Use streaming TTS — audio starts playing as chunks arrive
      const { audio } = await api.textToSpeechStreamAndPlay(
        text,
        undefined, // use default voice
        // onStart — audio began playing
        () => {
          // Calculate exact latency: VAD stop to first byte of TTS playback
          if (vadStopTimestampRef.current) {
            setVoiceLatencyMs(performance.now() - vadStopTimestampRef.current);
            vadStopTimestampRef.current = null;
          }
          // Clear processing state (seamless transition)
          optionsRef.current.setIsProcessingQuery(false);
          setIsProcessingVoice(false);
          optionsRef.current.setIsCurrentInputVoice(false);
          optionsRef.current.setHasTamilInput(false);

          setIsSpeaking(true);
          navigator.vibrate?.(100);
        },
        // onEnd — audio finished playing
        () => {
          setIsSpeaking(false);
          setSpeakingMessageId(null);
          audioRef.current = null;

          // Clear caption after delay (if not resuming recording)
          setTimeout(() => {
            if (!shouldResumeRecording.current) {
              optionsRef.current.setLiveCaption(null);
            }
          }, 2000);

          // Auto-resume recording in always-on mode
          if (shouldResumeRecording.current) {
            setTimeout(() => {
              if (shouldResumeRecording.current) {
                resumeRecording();
              }
            }, 100);
          }
        },
        // onError
        (error) => {
          console.error('TTS playback error:', error);
          setIsSpeaking(false);
          setSpeakingMessageId(null);
          audioRef.current = null;
        }
      );

      audioRef.current = audio;
    } catch (error) {
      console.error('TTS error:', error);
      setIsSpeaking(false);
      setSpeakingMessageId(null);
      audioRef.current = null;
      // Reset processing state so UI doesn't stay stuck
      optionsRef.current.setIsProcessingQuery(false);
      setIsProcessingVoice(false);
      optionsRef.current.setIsCurrentInputVoice(false);
      optionsRef.current.setHasTamilInput(false);
    }
  };

  const stopTextToSpeech = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
      setIsSpeaking(false);
      setSpeakingMessageId(null);
    }
  };

  // ===== Recording =====

  const resumeRecording = async () => {
    if (!shouldResumeRecording.current) {
      return;
    }

    if (!shouldResumeRecording.current) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      const chunks: Blob[] = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.push(event.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop());

        if (userAbortedRef.current) {
          userAbortedRef.current = false;
          setIsProcessingVoice(false);
          return;
        }

        if (chunks.length === 0) return;

        const audioBlob = new Blob(chunks, { type: 'audio/webm;codecs=opus' });

        try {
          setIsProcessingVoice(true);
          const text = await api.transcribeAudio(audioBlob);

          // Filter out empty, too-short, or STT noise markers
          const trimmedResume = text?.trim() ?? '';
          const isNoiseResume = /^\[.*\]$/.test(trimmedResume);
          const cleanResume = trimmedResume.replace(/[?.!,;:'"()[\]{}<>]/g, '').trim();
          if (!cleanResume || cleanResume.length < 2 || isNoiseResume) {
            if (shouldResumeRecording.current) resumeRecording();
            return;
          }

          // Speech detected — cancel the no-speech timer
          hadSpeechRef.current = true;
          if (noSpeechTimeoutRef.current) {
            clearTimeout(noSpeechTimeoutRef.current);
            noSpeechTimeoutRef.current = null;
          }

          // Update live caption
          optionsRef.current.setLiveCaption({ text, type: 'user' });

          // Check for farewell
          if (await handleFarewell(text)) return;

          // Normal message flow
          setIsVoiceMode(true);
          setIsProcessingVoice(false);
          await optionsRef.current.sendMessage(text, true, true);
          // TTS onended will call resumeRecording again
        } catch (err) {
          console.error('❌ Voice processing error:', err);
          toast.error("Voice processing failed");
          setIsProcessingVoice(false);
          if (shouldResumeRecording.current) resumeRecording();
        }
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);

      setupVAD(stream, recorder);
      setRecordingTimeout(recorder);
    } catch (err) {
      console.error('❌ Failed to resume recording:', err);
      setIsAlwaysOnMode(false);
      shouldResumeRecording.current = false;
      toast.error("Microphone access lost");
    }
  };

  const abruptEndVoiceMode = () => {
    userAbortedRef.current = true;

    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.stop();
    }
    setIsRecording(false);
    activeRecordingRef.current = false;

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
    setIsSpeaking(false);
    setSpeakingMessageId(null);

    stopVAD();

    if (recordingTimeoutRef.current) {
      clearTimeout(recordingTimeoutRef.current);
      recordingTimeoutRef.current = null;
    }
    if (voiceModeTimeoutRef.current) {
      clearTimeout(voiceModeTimeoutRef.current);
      voiceModeTimeoutRef.current = null;
    }
    if (noSpeechTimeoutRef.current) {
      clearTimeout(noSpeechTimeoutRef.current);
      noSpeechTimeoutRef.current = null;
    }

    setIsAlwaysOnMode(false);
    shouldResumeRecording.current = false;
    hadSpeechRef.current = false;
    vadStopTimestampRef.current = null;
    setVoiceLatencyMs(null);

    setIsProcessingVoice(false);
    setIsVoiceMode(false);
    setIsFullscreenVoice(false);

    setTimeout(() => { userAbortedRef.current = false; }, 100);
  };

  const handleVoiceToggle = async () => {
    if (isTogglingVoiceRef.current) {
      return;
    }

    const opts = optionsRef.current;

    if (!opts.activeChat) {
      toast.error("No active chat");
      return;
    }

    if (!opts.isConnectionVerified) {
      toast.error("Data not loaded yet", { description: "Please wait for the data to load." });
      return;
    }

    isTogglingVoiceRef.current = true;

    try {
      const newIsRecording = !isRecording;

      if (newIsRecording && activeRecordingRef.current) {
        return;
      }

      setIsRecording(newIsRecording);
      activeRecordingRef.current = newIsRecording;

      // Haptic feedback
      if (newIsRecording) {
        navigator.vibrate?.(50);
      } else {
        navigator.vibrate?.([30, 50, 30]);
      }

      if (newIsRecording) {
        // === Start Recording ===
        opts.setExpandedVoiceSection(null);
        userAbortedRef.current = false;
        hadSpeechRef.current = false;
        setIsFullscreenVoice(true);
        setIsAlwaysOnMode(true);
        shouldResumeRecording.current = true;

        // Start no-speech cancel timer — if no speech within 5s, exit voice mode
        if (noSpeechTimeoutRef.current) clearTimeout(noSpeechTimeoutRef.current);
        noSpeechTimeoutRef.current = setTimeout(() => {
          if (!hadSpeechRef.current) {
            toast.error("No speech detected", { description: "Voice mode cancelled." });
            abruptEndVoiceMode();
          }
          noSpeechTimeoutRef.current = null;
        }, NO_SPEECH_CANCEL_TIMEOUT);

        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
          const chunks: Blob[] = [];

          recorder.ondataavailable = (event) => {
            if (event.data.size > 0) chunks.push(event.data);
          };

          recorder.onstop = async () => {
            activeRecordingRef.current = false;
            stream.getTracks().forEach(track => track.stop());

            if (userAbortedRef.current) {
              userAbortedRef.current = false;
              setIsProcessingVoice(false);
              return;
            }

            const audioBlob = new Blob(chunks, { type: 'audio/webm;codecs=opus' });

            try {
              setIsProcessingVoice(true);
              const text = await api.transcribeAudio(audioBlob);

              // Filter out empty, too-short, or STT noise markers
              const trimmed = text?.trim() ?? '';
              const isNoiseMarker = /^\[.*\]$/.test(trimmed); // e.g. [typing], [background noise], [outro jingle]
              const cleanText = trimmed.replace(/[?.!,;:'"()[\]{}<>]/g, '').trim();
              if (!cleanText || cleanText.length < 2 || isNoiseMarker) {
                // Don't show toast here — the no-speech timer handles the cancel
                optionsRef.current.setLiveCaption(null);
                setIsProcessingVoice(false);
                return;
              }

              // Speech detected — cancel the no-speech timer
              hadSpeechRef.current = true;
              if (noSpeechTimeoutRef.current) {
                clearTimeout(noSpeechTimeoutRef.current);
                noSpeechTimeoutRef.current = null;
              }

              // Update live caption
              optionsRef.current.setLiveCaption({ text, type: 'user' });

              // Check for farewell
              if (await handleFarewell(text)) return;

              // Normal message flow
              setIsVoiceMode(true);

              // Keep isProcessingVoice=true until handleSendMessage sets isProcessingQuery
              await optionsRef.current.sendMessage(text, true, true);

              // Voice mode timeout (disable after period of inactivity)
              if (voiceModeTimeoutRef.current) clearTimeout(voiceModeTimeoutRef.current);
              voiceModeTimeoutRef.current = setTimeout(() => {
                setIsVoiceMode(false);
                voiceModeTimeoutRef.current = null;
              }, VOICE_MODE_TIMEOUT);
            } catch (err) {
              console.error('❌ Voice processing error:', err);
              toast.error("Voice processing failed", {
                description: err instanceof Error ? err.message : "Unknown error"
              });
            } finally {
              setIsProcessingVoice(false);
            }
          };

          recorder.start();
          setMediaRecorder(recorder);

          setupVAD(stream, recorder);
          setRecordingTimeout(recorder);
        } catch (err) {
          console.error('❌ Microphone access error:', err);
          toast.error("Microphone access denied", {
            description: "Please allow microphone access to use voice input."
          });
          setIsRecording(false);
          activeRecordingRef.current = false;
        }
      } else {
        // === Manual Stop ===
        setIsFullscreenVoice(false);
        setIsAlwaysOnMode(false);
        shouldResumeRecording.current = false;
        hadSpeechRef.current = false;
        vadStopTimestampRef.current = null;
        setVoiceLatencyMs(null);
        stopVAD();

        if (recordingTimeoutRef.current) {
          clearTimeout(recordingTimeoutRef.current);
          recordingTimeoutRef.current = null;
        }
        if (noSpeechTimeoutRef.current) {
          clearTimeout(noSpeechTimeoutRef.current);
          noSpeechTimeoutRef.current = null;
        }
        if (mediaRecorder && mediaRecorder.state === 'recording') {
          mediaRecorder.stop();
        }
        activeRecordingRef.current = false;
      }
    } finally {
      setTimeout(() => { isTogglingVoiceRef.current = false; }, 100);
    }
  };

  // ===== Return =====
  return {
    // State
    isRecording,
    isProcessingVoice,
    isSpeaking,
    isVoiceMode,
    isAlwaysOnMode,
    isFullscreenVoice,
    isVoiceEnabledInChat,
    setIsVoiceEnabledInChat,
    speakingMessageId,
    voiceLatencyMs,
    // Functions
    handleVoiceToggle,
    abruptEndVoiceMode,
    playTextToSpeech,
    stopTextToSpeech,
  };
}
