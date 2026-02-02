'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppState } from '@/lib/hooks';
import { MessageBubble } from './MessageBubble';
import { VoiceVisualizer } from './VoiceVisualizer';
import { ProcessingStatus } from './ProcessingStatus';
import { api } from '@/services/api';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  LogOut,
  Mic,
  MicOff,
  Square,
  MessageCircle,
  ChevronLeft,
  MoreHorizontal,
  Table,
  History,
  X,
  Plus,
  Trash2,
  Sparkles,
  MessageSquarePlus,
  ChevronRight,
  Settings,
  Zap,
  User,
  Send,
  Sun,
  Moon,
  Monitor,
  Loader2,
  RefreshCw,
  StopCircle,
  Pencil,
  Check,
  Eraser,
  Search,
  PanelLeftClose,
  PanelLeft,
  PhoneOff
} from 'lucide-react';
import { toast } from 'sonner';
import { useTheme } from 'next-themes';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { ChatTab } from '@/lib/types';
// DatasetConnection removed - using demo mode only
import { DatasetInfoPopover, DatasetInfo } from './DatasetInfoPopover';
import {
  VOICE_RECORDING_TIMEOUT,
  VOICE_MODE_TIMEOUT,
  VAD_SILENCE_THRESHOLD,
  VAD_SILENCE_DURATION,
  VAD_MIN_SPEECH_DURATION,
  VAD_CHECK_INTERVAL
} from '@/lib/constants';

interface ChatScreenProps {
  onLogout: () => void;
  username: string;
}

// Typing animation pill component
function TypingPlaceholderPill({
  suggestions,
  onSelect
}: {
  suggestions: string[];
  onSelect: (suggestion: string) => void;
}) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [displayText, setDisplayText] = useState('');
  const [isTyping, setIsTyping] = useState(true);

  useEffect(() => {
    const currentSuggestion = suggestions[currentIndex];
    let charIndex = 0;
    let timeout: NodeJS.Timeout;

    if (isTyping) {
      // Typing effect
      const typeChar = () => {
        if (charIndex <= currentSuggestion.length) {
          setDisplayText(currentSuggestion.slice(0, charIndex));
          charIndex++;
          timeout = setTimeout(typeChar, 50); // Typing speed
        } else {
          // Pause at the end before erasing
          timeout = setTimeout(() => setIsTyping(false), 2000);
        }
      };
      typeChar();
    } else {
      // Erasing effect
      let eraseIndex = currentSuggestion.length;
      const eraseChar = () => {
        if (eraseIndex >= 0) {
          setDisplayText(currentSuggestion.slice(0, eraseIndex));
          eraseIndex--;
          timeout = setTimeout(eraseChar, 30); // Erasing speed (faster)
        } else {
          // Move to next suggestion
          setCurrentIndex((prev) => (prev + 1) % suggestions.length);
          setIsTyping(true);
        }
      };
      eraseChar();
    }

    return () => clearTimeout(timeout);
  }, [currentIndex, isTyping, suggestions]);

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onSelect(suggestions[currentIndex])}
      className="group relative cursor-pointer"
    >
      <div className="flex items-center gap-2 sm:gap-3 h-11 sm:h-14 px-4 sm:px-6 rounded-full bg-zinc-900/80 border border-zinc-700/50 hover:border-violet-500/50 hover:bg-zinc-800/80 transition-all duration-300 backdrop-blur-xl shadow-lg shadow-black/20">
        <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 text-violet-400 shrink-0" />
        <div className="flex-1 overflow-hidden">
          <span className="text-zinc-400 text-xs sm:text-sm font-medium">
            {displayText}
            <motion.span
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.5, repeat: Infinity, repeatType: "reverse" }}
              className="inline-block w-0.5 h-3 sm:h-4 bg-violet-400 ml-0.5 align-middle"
            />
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-zinc-500 hidden sm:inline">Click to ask</span>
          <ChevronRight className="w-4 h-4 text-zinc-500 group-hover:text-violet-400 group-hover:translate-x-0.5 transition-all" />
        </div>
      </div>
    </motion.div>
  );
}

// Suggested follow-up questions (English and Tamil)
const FOLLOW_UP_SUGGESTIONS = [
  "Are sales increasing or decreasing in Chennai?",
  "சென்னை நகரத்தில் sales உயர்கிறதா குறைகிறதா?",
  "Which state shows a declining sales trend?",
  "எந்த state-இல் sales trend குறைந்து வருகிறது?",
  "Which category shows consistent growth across months?",
  "எந்த category மாதம் முழுவதும் நிலையான வளர்ச்சியை காட்டுகிறது?",
  "Are profits stable or volatile over time?",
  "profit காலப்போக்கில் நிலையானதா அல்லது மாறுபடுகிறதா?",
  "Which month had an unusual spike in sales?",
  "எந்த மாதத்தில் sales திடீரென அதிகரித்தது?",
  "Is revenue seasonally higher in certain months?",
  "சில மாதங்களில் revenue அதிகமாக இருக்கிறதா?",
  "Which branch shows declining performance?",
  "எந்த branch செயல்திறன் குறைந்து வருகிறது?",
  "Which category is losing revenue month by month?",
  "எந்த category மாதம் மாதமாக revenue இழக்கிறது?",
  "Are costs rising faster than revenue?",
  "revenue-விட cost வேகமாக உயருகிறதா?",
  "Which quarter performed the worst overall?",
  "மொத்தமாக எந்த quarter மோசமாக செயல்பட்டது?",
];

// Get 2 random suggestions
function getRandomSuggestions(): string[] {
  const shuffled = [...FOLLOW_UP_SUGGESTIONS].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, 2);
}

export function ChatScreen({ onLogout, username }: ChatScreenProps) {
  const {
    messages,
    addMessage,
    config,
    chatTabs,
    activeChatId,
    isInitializing,
    createNewChat,
    switchChat,
    deleteChat,
    renameChat,
    getCurrentChat,
    setDatasetForChat,
    clearCurrentChat
  } = useAppState();

  const [isRecording, setIsRecording] = useState(false);
  const [isProcessingVoice, setIsProcessingVoice] = useState(false);
  // Track if we have verified the connection with the backend (honest UI)
  const [isConnectionVerified, setIsConnectionVerified] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [showChatsPanel, setShowChatsPanel] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { theme, setTheme } = useTheme();

  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [audioChunks, setAudioChunks] = useState<Blob[]>([]);
  // Voice enabled toggle for chat mode (home screen always has voice on)
  const [isVoiceEnabledInChat, setIsVoiceEnabledInChat] = useState(false);
  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [editingChatTitle, setEditingChatTitle] = useState('');

  // Always-on voice mode state
  const [isAlwaysOnMode, setIsAlwaysOnMode] = useState(false);
  const shouldResumeRecording = useRef(false);
  // Ref mirror for isAlwaysOnMode to avoid stale closures in callbacks
  const isAlwaysOnModeRef = useRef(false);
  // Track if user manually aborted recording (should not process audio)
  const userAbortedRef = useRef(false);

  // Keep ref in sync with state
  useEffect(() => {
    isAlwaysOnModeRef.current = isAlwaysOnMode;
  }, [isAlwaysOnMode]);

  // Audio ref to control TTS playback (stop functionality)
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Track which message is currently speaking
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);

  // Timeout refs for cleanup (prevent memory leaks)
  const voiceModeTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const recordingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Voice Activity Detection (VAD) refs for fast silence detection
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const vadIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const silenceStartRef = useRef<number | null>(null);
  const speechStartRef = useRef<number | null>(null);

  /* New State for Voice Section Toggles - REMOVED, replaced with suggestion UI */
  const [expandedVoiceSection, setExpandedVoiceSection] = useState<'plan' | 'data' | 'schema' | null>(null);

  // Search state for sidebar
  const [searchQuery, setSearchQuery] = useState('');

  // Processing status tracking for UI feedback
  const [isProcessingQuery, setIsProcessingQuery] = useState(false);
  const [isCurrentInputVoice, setIsCurrentInputVoice] = useState(false);
  const [hasTamilInput, setHasTamilInput] = useState(false);

  // Demo mode state - when true, show info button instead of connection dialog
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [demoDatasetInfo, setDemoDatasetInfo] = useState<DatasetInfo | null>(null);

  // Fullscreen call mode - hides header for immersive phone-call experience on mobile
  const [isFullscreenVoice, setIsFullscreenVoice] = useState(false);

  // Follow-up suggestions state - refreshed after each assistant response
  const [followUpSuggestions, setFollowUpSuggestions] = useState<string[]>(() => getRandomSuggestions());

  // Helper to detect concluding/farewell phrases
  const isConcludingPhrase = (text: string): boolean => {
    const normalizedText = text.toLowerCase().trim();
    const concludingPhrases = [
      // Thank you variations
      'thank you', 'thanks', 'thank you so much', 'thanks a lot', 'many thanks',
      // Okay/acknowledgment
      'okay', 'ok', 'alright', 'all right', 'got it', 'understood',
      // Farewell
      'bye', 'goodbye', 'good bye', 'see you', 'take care',
      // Done/finished
      'that\'s all', 'that\'s it', 'i\'m done', 'im done', 'done', 'finished',
      'nothing else', 'no more questions', 'that will be all',
      // Tamil concluding phrases
      'நன்றி', 'போய் வருகிறேன்', 'சரி'
    ];

    // Check for exact match or if text starts with concluding phrase
    return concludingPhrases.some(phrase =>
      normalizedText === phrase ||
      normalizedText.startsWith(phrase + ' ') ||
      normalizedText.endsWith(' ' + phrase)
    );
  };

  // Get a random farewell response
  const getFarewellResponse = (): string => {
    const responses = [
      "You're welcome! Feel free to ask anytime. Goodbye!",
      "Happy to help! Have a great day!",
      "Glad I could assist! Take care!",
      "Anytime! See you next time!",
      "My pleasure! Don't hesitate to come back if you need anything.",
      "Thank you for using Thara! Goodbye!"
    ];
    return responses[Math.floor(Math.random() * responses.length)];
  };

  useEffect(() => {
    // Scroll to bottom when messages change, chat opens, or switching chats
    const scrollToBottom = () => {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    };
    // Multiple scroll attempts to handle layout shifts and async rendering
    // Chat entry animation is 500ms, so we need timeouts up to 600ms
    scrollToBottom();
    const t1 = setTimeout(scrollToBottom, 50);
    const t2 = setTimeout(scrollToBottom, 150);
    const t3 = setTimeout(scrollToBottom, 350);
    const t4 = setTimeout(scrollToBottom, 600); // After animation completes
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
    };
  }, [messages.length, showChat, activeChatId]);

  // Cleanup timeouts and VAD on unmount to prevent memory leaks
  useEffect(() => {
    return () => {
      if (voiceModeTimeoutRef.current) {
        clearTimeout(voiceModeTimeoutRef.current);
      }
      if (recordingTimeoutRef.current) {
        clearTimeout(recordingTimeoutRef.current);
      }
      if (vadIntervalRef.current) {
        clearInterval(vadIntervalRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  // Helper to stop VAD monitoring
  const stopVAD = () => {
    if (vadIntervalRef.current) {
      clearInterval(vadIntervalRef.current);
      vadIntervalRef.current = null;
    }
    silenceStartRef.current = null;
    speechStartRef.current = null;
  };

  // Abruptly end voice mode - stops everything immediately without processing
  const abruptEndVoiceMode = () => {
    console.log('🔴 Abruptly ending voice mode...');

    // 1. Mark as aborted to prevent any pending audio from being processed
    userAbortedRef.current = true;

    // 2. Stop recording if active
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.stop();
    }
    setIsRecording(false);
    activeRecordingRef.current = false;

    // 3. Stop TTS if playing
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
    setIsSpeaking(false);
    setSpeakingMessageId(null);

    // 4. Stop VAD
    stopVAD();

    // 5. Clear all timeouts
    if (recordingTimeoutRef.current) {
      clearTimeout(recordingTimeoutRef.current);
      recordingTimeoutRef.current = null;
    }
    if (voiceModeTimeoutRef.current) {
      clearTimeout(voiceModeTimeoutRef.current);
      voiceModeTimeoutRef.current = null;
    }

    // 6. Disable always-on mode
    setIsAlwaysOnMode(false);
    shouldResumeRecording.current = false;

    // 7. Clear processing states
    setIsProcessingVoice(false);
    setIsVoiceMode(false);

    // 8. Exit fullscreen
    setIsFullscreenVoice(false);

    // 9. Reset abort flag after a short delay (for next session)
    setTimeout(() => {
      userAbortedRef.current = false;
    }, 100);

    console.log('✅ Voice mode ended abruptly');
  };

  const activeChat = getCurrentChat();

  // Track if this is the initial mount (for verification logic)
  const hasVerifiedOnce = useRef(false);

  // EFFECT: Check if dataset was previously connected (don't auto-reload)
  // We trust the stored state - user must manually sync if they want fresh data
  useEffect(() => {
    if (activeChat?.datasetStatus === 'ready' && activeChat?.datasetUrl) {
      // Trust stored state - mark as verified without re-loading
      // User can click "Sync" button if they want to refresh data
      setIsConnectionVerified(true);
      hasVerifiedOnce.current = true;
      console.log("✅ Using stored dataset state (no auto-reload)");
    } else if (!isDemoMode) {
      // Only reset verification if NOT in demo mode
      // Demo mode data is pre-loaded on the backend, so we trust it
      setIsConnectionVerified(false);
    }
  }, [activeChat?.datasetStatus, activeChat?.datasetUrl, isDemoMode]);

  // EFFECT: Stop recording when voice is disabled in chat mode
  useEffect(() => {
    if (!isVoiceEnabledInChat && isRecording && showChat) {
      console.log('🔇 Voice disabled in chat - stopping recording');
      if (mediaRecorder && mediaRecorder.state === 'recording') {
        userAbortedRef.current = true; // Don't process the audio
        mediaRecorder.stop();
      }
      setIsRecording(false);
    }
  }, [isVoiceEnabledInChat, isRecording, showChat, mediaRecorder]);

  // EFFECT: Check for demo mode (pre-loaded dataset) on mount
  // If backend has pre-loaded data, skip the connection dialog entirely
  useEffect(() => {
    const checkDemoMode = async () => {
      try {
        const response = await api.getDatasetStatus();
        if (response.loaded && response.demo_mode) {
          console.log("✅ Demo mode: Dataset pre-loaded, skipping connection dialog");
          setIsConnectionVerified(true);
          hasVerifiedOnce.current = true;

          // Set demo mode flag and dataset info for the info popover
          setIsDemoMode(true);
          const demoInfo: DatasetInfo = {
            totalTables: response.total_tables || 0,
            totalRecords: response.total_records || 0,
            sheetCount: response.original_sheets?.length || response.tables?.length || 2,
            sheets: response.original_sheets || [],  // Use original sheet names, not DuckDB table names
            detectedTables: response.detected_tables || []
          };
          setDemoDatasetInfo(demoInfo);

          // Create a chat if NO CHATS EXIST (not just if no active chat)
          if (chatTabs.length === 0) {
            createNewChat();
          }

          // Update ALL existing chats with demo dataset info (fixes stale localStorage)
          const demoStats = {
            totalTables: demoInfo.totalTables,
            totalRecords: demoInfo.totalRecords,
            sheetCount: demoInfo.sheetCount,
            sheets: demoInfo.sheets,
            detectedTables: demoInfo.detectedTables || []
          };

          // Update each chat that doesn't have 'ready' status
          chatTabs.forEach(chat => {
            if (chat.datasetStatus !== 'ready') {
              setDatasetForChat('demo://preloaded', 'ready', demoStats, chat.id);
            }
          });
        }
      } catch (error) {
        // Not in demo mode, normal flow continues
        console.log("Demo mode check: Not in demo mode or backend not ready");
        setIsDemoMode(false);
      }
    };

    // Only check once on mount AND after initialization is complete
    if (!hasVerifiedOnce.current && !isInitializing) {
      checkDemoMode();
    }
  }, [activeChatId, chatTabs, createNewChat, setDatasetForChat, isInitializing]);

  const handleSendMessage = async (content: string, shouldPlayTTS: boolean = false, isVoiceInput: boolean = false) => {
    if (!activeChatId && chatTabs.length === 0) {
      createNewChat();
    }

    // Check for dataset connection (allow demo mode)
    const currentChat = activeChatId ? chatTabs.find(t => t.id === activeChatId) : null;
    if (!isConnectionVerified && (!currentChat || currentChat.datasetStatus !== 'ready')) {
      // Double-check demo mode before showing error
      try {
        const statusResp = await api.getDatasetStatus();
        if (statusResp.loaded) {
          setIsConnectionVerified(true);
          // Continue with the message
        } else {
          toast.error("Data not loaded", { description: "Please wait for the data to load or refresh the page." });
          return;
        }
      } catch {
        toast.error("Connection error", { description: "Could not verify data connection." });
        return;
      }
    }

    // Detect Tamil characters in input
    const containsTamil = /[\u0B80-\u0BFF]/.test(content);

    // Set processing state for UI feedback
    setIsProcessingQuery(true);
    setIsCurrentInputVoice(isVoiceInput);
    setHasTamilInput(containsTamil);

    addMessage(content, 'user');

    // Call API with delay
    try {
      const response = await api.sendMessage(content);

      if (response.success) {
        addMessage(response.explanation, 'assistant', {
          plan: response.plan,
          data: response.data,
          schema_context: response.schema_context,
          data_refreshed: response.data_refreshed,
          visualization: response.visualization
        });

        // Auto-expand Query Plan if available
        if (response.plan) {
          setExpandedVoiceSection('plan');
        }

        // Refresh follow-up suggestions for the user
        setFollowUpSuggestions(getRandomSuggestions());

        // NOTE: Keep isProcessingQuery=true until TTS is ready to play
        // This prevents "Ready..." gap while fetching TTS audio (2-4 seconds)
        // isProcessingQuery will be cleared inside playTextToSpeech

        // Play TTS response with Rachel voice
        console.log('🔊 shouldPlayTTS:', shouldPlayTTS);
        console.log('📝 Response explanation:', response.explanation.substring(0, 50));

        if (shouldPlayTTS) {
          console.log('✅ Playing TTS...');
          await playTextToSpeech(response.explanation);
        } else {
          console.log('⚠️ TTS disabled (flag not set)');
          // Clear processing state since we're not playing TTS
          setIsProcessingQuery(false);
          setIsProcessingVoice(false);
          setIsCurrentInputVoice(false);
          setHasTamilInput(false);
        }

      } else {
        // Use explanation (user-friendly) with fallback to error message
        const errorMsg = response.explanation || response.error || "Sorry, I encountered an error extracting that information.";
        toast.error("Query failed", { description: errorMsg });
        addMessage(errorMsg, 'assistant');
      }

    } catch (error: unknown) {
      console.error('Send message error:', error);
      // Provide more specific error messages
      let errorMessage = "Network connection error. Please try again.";
      if (error instanceof Error) {
        if (error.message.includes('timeout') || error.message.includes('abort')) {
          errorMessage = "Request timed out. The server might be busy. Please try again.";
        } else if (error.message.includes('Failed to fetch')) {
          errorMessage = "Cannot reach the server. Please check if the backend is running.";
        } else if (error.name === 'TypeError') {
          errorMessage = "Connection issue. Please refresh and try again.";
        }
      }
      addMessage(errorMessage, 'assistant');
    } finally {
      // Reset processing state
      setIsProcessingQuery(false);
      setIsCurrentInputVoice(false);
      setHasTamilInput(false);
    }
  };

  const playTextToSpeech = async (text: string, messageId?: string) => {
    try {
      // Stop any currently playing audio first
      if (audioRef.current) {
        console.log('⏹️ Stopping previous TTS before starting new one');
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
        audioRef.current = null;
      }

      // Set message ID for loading indicator (but NOT speaking yet)
      setSpeakingMessageId(messageId || null);
      console.log('🔊 Fetching TTS for:', text.substring(0, 50) + '...');

      // Call TTS endpoint via API service (this takes time - ~2-4 seconds)
      const audioBlob = await api.textToSpeech(text);
      console.log('✅ Received audio blob:', audioBlob.size, 'bytes');

      // Check if audio blob is valid
      if (!audioBlob || audioBlob.size === 0) {
        console.error('❌ Empty audio blob received');
        toast.error("Voice response unavailable", { description: "Could not generate audio" });
        setSpeakingMessageId(null);
        return;
      }

      // Clear processing state RIGHT BEFORE setting speaking state
      // This ensures seamless transition: Processing -> Speaking (no "Ready..." gap)
      setIsProcessingQuery(false);
      setIsProcessingVoice(false);
      setIsCurrentInputVoice(false);
      setHasTamilInput(false);

      // NOW set speaking state - audio is ready to play
      setIsSpeaking(true);

      // Haptic feedback when TTS is actually ready to play
      navigator.vibrate?.(100);

      // Create audio URL and play
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);

      // Store reference for stop functionality
      audioRef.current = audio;

      audio.onended = () => {
        console.log('✅ TTS playback finished');
        setIsSpeaking(false);
        setSpeakingMessageId(null);
        audioRef.current = null;
        URL.revokeObjectURL(audioUrl);

        // Auto-resume recording if in always-on mode
        // Use ref (shouldResumeRecording) instead of state (isAlwaysOnMode) to avoid stale closure
        if (shouldResumeRecording.current) {
          console.log('🎤 Always-on mode: Auto-resuming recording after TTS');
          // Small delay to ensure audio is fully released, then resume
          setTimeout(() => {
            if (shouldResumeRecording.current) {
              resumeRecording();
            }
          }, 100);
        }
      };

      audio.onerror = () => {
        // Access audio.error for actual error details
        const errorCode = audio.error?.code;
        const errorMsg = audio.error?.message || 'Unknown audio error';
        console.error('❌ Audio playback error:', errorCode, errorMsg);
        setIsSpeaking(false);
        setSpeakingMessageId(null);
        audioRef.current = null;
        URL.revokeObjectURL(audioUrl);
      };

      try {
        await audio.play();
        audio.playbackRate = 1.1;  // 30% faster playback
        console.log('▶️ TTS playback started at 1.3x speed');
      } catch (playError) {
        // Handle autoplay policy - browser blocks audio without user interaction
        if (playError instanceof Error && playError.name === 'NotAllowedError') {
          console.warn('⚠️ Autoplay blocked by browser policy - user can click Play button');
          // Don't show error toast - user can manually click Play on the message
          setIsSpeaking(false);
          setSpeakingMessageId(null);
          audioRef.current = null;
          URL.revokeObjectURL(audioUrl);
          return; // Exit silently - user can manually play
        }
        throw playError; // Re-throw other errors
      }

    } catch (error) {
      console.error('❌ TTS error:', error);
      setIsSpeaking(false);
      setSpeakingMessageId(null);
      audioRef.current = null;
      toast.error('Voice playback failed', {
        description: 'Could not play audio response'
      });
    }
  };

  // Stop TTS playback
  const stopTextToSpeech = () => {
    if (audioRef.current) {
      console.log('⏹️ Stopping TTS playback');
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
      setIsSpeaking(false);
      setSpeakingMessageId(null);
    }
  };

  // Resume recording for always-on voice mode
  const resumeRecording = async () => {
    // Use ref check to avoid stale closure issues
    if (!shouldResumeRecording.current) {
      console.log('🎤 Not resuming: always-on mode disabled');
      return;
    }

    console.log('🎤 Auto-resuming recording in always-on mode...');

    // Check again in case user clicked stop
    if (!shouldResumeRecording.current) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
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
        stream.getTracks().forEach(track => track.stop());

        // Check if user manually aborted
        if (userAbortedRef.current) {
          console.log('⏹️ User aborted resumed recording - skipping processing');
          userAbortedRef.current = false;
          setIsProcessingVoice(false);
          return;
        }

        if (chunks.length === 0) return;

        const audioBlob = new Blob(chunks, { type: 'audio/webm;codecs=opus' });
        console.log('📦 Audio blob size:', audioBlob.size, 'bytes');

        try {
          setIsProcessingVoice(true);
          const text = await api.transcribeAudio(audioBlob);
          console.log('✅ Transcribed text:', text);

          if (!text || text.trim() === '') {
            console.warn('⚠️ Empty transcription - waiting for next input...');
            // In always-on mode, just resume listening instead of showing error
            if (shouldResumeRecording.current) {
              resumeRecording();
            }
            return;
          }

          // Check if this is a concluding phrase (thank you, bye, etc.)
          if (isConcludingPhrase(text)) {
            console.log('👋 Concluding phrase detected in resumed recording:', text);

            // Add user message
            addMessage(text, 'user');

            // Add farewell response
            const farewellMsg = getFarewellResponse();
            addMessage(farewellMsg, 'assistant');

            // Play farewell TTS
            setIsVoiceMode(true);
            await playTextToSpeech(farewellMsg);

            // Stop always-on mode and exit fullscreen
            setIsAlwaysOnMode(false);
            shouldResumeRecording.current = false;
            setIsFullscreenVoice(false);
            setIsProcessingVoice(false);

            toast.success("Conversation ended", { description: "Tap mic to start again" });
            return;
          }

          setIsVoiceMode(true);
          setIsProcessingVoice(false);

          // Send transcribed message WITH TTS enabled
          await handleSendMessage(text, true, true);

          // Note: TTS onended will call resumeRecording again

        } catch (err) {
          console.error('❌ Voice processing error:', err);
          toast.error("Voice processing failed");
          setIsProcessingVoice(false);
          // Resume recording despite error in always-on mode
          if (shouldResumeRecording.current) {
            resumeRecording();
          }
        }
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
      console.log('🔴 Recording resumed in always-on mode');

      // === VAD for resumed recording ===
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

        console.log('🎙️ VAD started for resumed recording...');

        vadIntervalRef.current = setInterval(() => {
          if (!analyserRef.current || recorder.state !== 'recording') {
            stopVAD();
            return;
          }

          analyser.getByteFrequencyData(dataArray);
          const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;

          const now = Date.now();
          const speechDuration = now - (speechStartRef.current || now);

          if (speechDuration < VAD_MIN_SPEECH_DURATION) {
            return;
          }

          if (average < VAD_SILENCE_THRESHOLD) {
            if (!silenceStartRef.current) {
              silenceStartRef.current = now;
            } else if (now - silenceStartRef.current > VAD_SILENCE_DURATION) {
              console.log('✋ VAD: Silence detected - stopping resumed recording');
              stopVAD();
              if (recorder.state === 'recording') {
                recorder.stop();
                setIsRecording(false);
              }
            }
          } else {
            silenceStartRef.current = null;
          }
        }, VAD_CHECK_INTERVAL);

      } catch (vadError) {
        console.warn('⚠️ VAD setup failed in resume:', vadError);
      }

      // Fallback timeout
      if (recordingTimeoutRef.current) {
        clearTimeout(recordingTimeoutRef.current);
      }
      recordingTimeoutRef.current = setTimeout(() => {
        stopVAD();
        if (recorder.state === 'recording') {
          console.log('⏱️ Max timeout in resumed recording');
          recorder.stop();
          setIsRecording(false);
        }
        recordingTimeoutRef.current = null;
      }, VOICE_RECORDING_TIMEOUT);

    } catch (err) {
      console.error('❌ Failed to resume recording:', err);
      setIsAlwaysOnMode(false);
      shouldResumeRecording.current = false;
      toast.error("Microphone access lost");
    }
  };

  // Ref to prevent double-clicking on mic button (race condition prevention)
  const isTogglingVoiceRef = useRef(false);
  // Ref to track active recording session
  const activeRecordingRef = useRef(false);

  const handleVoiceToggle = async () => {
    // Prevent double-click issues - check both toggle lock AND active recording
    if (isTogglingVoiceRef.current) {
      console.log('⚠️ Voice toggle already in progress, ignoring...');
      return;
    }

    if (!activeChat) {
      toast.error("No active chat");
      return;
    }

    // In demo mode, data is pre-loaded
    if (!isConnectionVerified) {
      toast.error("Data not loaded yet", {
        description: "Please wait for the data to load."
      });
      return;
    }

    // Set toggle lock - will be released in finally block
    isTogglingVoiceRef.current = true;

    try {
      const newIsRecording = !isRecording;

      // Prevent starting a new recording if one is already active
      if (newIsRecording && activeRecordingRef.current) {
        console.log('⚠️ Recording already active, ignoring start request...');
        return;
      }

      setIsRecording(newIsRecording);
      activeRecordingRef.current = newIsRecording;

    // Haptic feedback for mobile
    if (newIsRecording) {
      // Short vibration pulse when starting to record
      navigator.vibrate?.(50);
    } else {
      // Double-pulse when stopping
      navigator.vibrate?.([30, 50, 30]);
    }

    if (newIsRecording) { // Started listening
      console.log('🎤 Started listening (always-on mode enabled)...');
      setExpandedVoiceSection(null);

      // Reset abort flag for new recording
      userAbortedRef.current = false;

      // Enable fullscreen voice mode for immersive experience
      setIsFullscreenVoice(true);

      // Enable always-on mode
      setIsAlwaysOnMode(true);
      shouldResumeRecording.current = true;

      try {
        // Request microphone access
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        // Create MediaRecorder
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

          // Mark recording as inactive
          activeRecordingRef.current = false;

          // Stop all tracks
          stream.getTracks().forEach(track => track.stop());

          // Check if user manually aborted - skip processing entirely
          if (userAbortedRef.current) {
            console.log('⏹️ User aborted - skipping audio processing');
            userAbortedRef.current = false; // Reset for next recording
            setIsProcessingVoice(false);
            return;
          }

          // Create audio blob from chunks
          const audioBlob = new Blob(chunks, { type: 'audio/webm;codecs=opus' });
          console.log('📦 Audio blob size:', audioBlob.size, 'bytes');

          try {
            console.log('📤 Sending audio for transcription...');
            setIsProcessingVoice(true); // Start loading UI
            const text = await api.transcribeAudio(audioBlob);
            console.log('✅ Transcribed text:', text);

            if (!text || text.trim() === '') {
              console.warn('⚠️ Empty transcription result');
              toast.error("No speech detected", { description: "Please try speaking again." });
              return;
            }

            // Check if this is a concluding phrase (thank you, bye, etc.)
            if (isConcludingPhrase(text)) {
              console.log('👋 Concluding phrase detected:', text);

              // Add user message
              addMessage(text, 'user');

              // Add farewell response
              const farewellMsg = getFarewellResponse();
              addMessage(farewellMsg, 'assistant');

              // Play farewell TTS
              setIsVoiceMode(true);
              await playTextToSpeech(farewellMsg);

              // Stop always-on mode and exit fullscreen
              setIsAlwaysOnMode(false);
              shouldResumeRecording.current = false;
              setIsFullscreenVoice(false);
              setIsProcessingVoice(false);

              toast.success("Conversation ended", { description: "Tap mic to start again" });
              return;
            }

            // Enable voice mode for TTS playback
            console.log('🔊 Enabling voice mode for TTS...');
            setIsVoiceMode(true);

            // NOTE: Keep isProcessingVoice=true until handleSendMessage sets isProcessingQuery
            // This prevents "Ready..." gap between transcription and query processing

            // Send transcribed message WITH TTS enabled and mark as voice input
            console.log('📤 Sending transcribed message with TTS...');
            await handleSendMessage(text, true, true); // TTS enabled + voice input flag

            // Keep voice mode enabled for a bit, then disable
            // Clear any previous timeout before setting a new one
            if (voiceModeTimeoutRef.current) {
              clearTimeout(voiceModeTimeoutRef.current);
            }
            voiceModeTimeoutRef.current = setTimeout(() => {
              console.log('🔇 Disabling voice mode');
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

        // Start recording
        recorder.start();
        setMediaRecorder(recorder);
        console.log('🔴 Recording started...');

        // === VOICE ACTIVITY DETECTION (VAD) for phone-call-like experience ===
        try {
          // Create AudioContext for analyzing audio levels
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

          console.log('🎙️ VAD started - listening for silence...');

          // Check audio levels periodically
          vadIntervalRef.current = setInterval(() => {
            if (!analyserRef.current || recorder.state !== 'recording') {
              stopVAD();
              return;
            }

            analyser.getByteFrequencyData(dataArray);
            // Calculate average audio level
            const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;

            const now = Date.now();
            const speechDuration = now - (speechStartRef.current || now);

            // Only check for silence after minimum speech duration
            if (speechDuration < VAD_MIN_SPEECH_DURATION) {
              return;
            }

            if (average < VAD_SILENCE_THRESHOLD) {
              // Silence detected
              if (!silenceStartRef.current) {
                silenceStartRef.current = now;
                console.log('🔇 Silence started...');
              } else if (now - silenceStartRef.current > VAD_SILENCE_DURATION) {
                // Silence duration exceeded - stop recording
                console.log('✋ VAD: Silence detected for', VAD_SILENCE_DURATION, 'ms - stopping recording');
                stopVAD();
                if (recorder.state === 'recording') {
                  recorder.stop();
                  setIsRecording(false);
                }
              }
            } else {
              // Speech detected - reset silence timer
              if (silenceStartRef.current) {
                console.log('🗣️ Speech resumed');
              }
              silenceStartRef.current = null;
            }
          }, VAD_CHECK_INTERVAL);

        } catch (vadError) {
          console.warn('⚠️ VAD setup failed, using timeout fallback:', vadError);
        }

        // Fallback: Auto-stop after max timeout (in case VAD fails)
        // Clear any previous timeout before setting a new one
        if (recordingTimeoutRef.current) {
          clearTimeout(recordingTimeoutRef.current);
        }
        recordingTimeoutRef.current = setTimeout(() => {
          stopVAD();
          if (recorder.state === 'recording') {
            console.log('⏱️ Max timeout reached - stopping recording');
            recorder.stop();
            setIsRecording(false);
          }
          recordingTimeoutRef.current = null;
        }, VOICE_RECORDING_TIMEOUT);

      } catch (err) {
        console.error('❌ Microphone access error:', err);
        toast.error("Microphone access denied", {
          description: "Please allow microphone access to use voice input."
        });
        setIsRecording(false);
        activeRecordingRef.current = false;
      }

    } else {
      // Manual stop - user clicked to stop recording
      console.log('🛑 Manually stopping recording...');

      // NOTE: Do NOT set userAbortedRef here - we want to process the audio!
      // userAbortedRef is only for cancellation, not for normal stop

      // Exit fullscreen voice mode
      setIsFullscreenVoice(false);

      // Disable always-on mode
      setIsAlwaysOnMode(false);
      shouldResumeRecording.current = false;

      // Clean up VAD
      stopVAD();

      // Clear the auto-stop timeout since we're manually stopping
      if (recordingTimeoutRef.current) {
        clearTimeout(recordingTimeoutRef.current);
        recordingTimeoutRef.current = null;
      }
      if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
      }
      // Mark recording as inactive when stopping
      activeRecordingRef.current = false;
    }
    } finally {
      // Always release the toggle lock after async operations complete
      // Use a small delay to prevent rapid re-triggering
      setTimeout(() => {
        isTogglingVoiceRef.current = false;
      }, 100);
    }
  };

  const handleNewChat = () => {
    createNewChat();
    setShowChatsPanel(false);
    toast.success("New conversation started");
  };

  // Filter chats based on search query
  const filteredChats = chatTabs.filter(tab =>
    tab.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    tab.messages.some(msg => msg.content.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="flex h-[100dvh] w-full overflow-hidden bg-background text-foreground">
      {/* Mobile Sidebar Backdrop */}
      <AnimatePresence>
        {showChatsPanel && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/50 z-40 md:hidden"
            onClick={() => setShowChatsPanel(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar - Width animation on desktop, slide on mobile */}
      <motion.div
        initial={false}
        animate={{ width: showChatsPanel ? 280 : 0 }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
        className="h-full overflow-hidden flex-shrink-0 hidden md:block"
      >
        <div className="w-[280px] h-full glass border-r border-border flex flex-col">
          {/* Sidebar Header */}
          <div className="p-4 border-b border-border">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold font-display tracking-tight">Your Chats</h3>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Close sidebar"
                onClick={() => setShowChatsPanel(false)}
                className="h-8 w-8 rounded-lg hover:bg-accent"
              >
                <PanelLeftClose className="w-4 h-4" />
              </Button>
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search chats..."
                className="pl-9 h-9 bg-muted/50 border-border focus:border-violet-500"
              />
            </div>
          </div>

          {/* New Chat Button */}
          <div className="p-3">
            <Button
              onClick={handleNewChat}
              className="w-full h-10 bg-violet-600 hover:bg-violet-500 text-white rounded-lg font-semibold gap-2 transition-all"
            >
              <Plus className="w-4 h-4" />
              New Chat
            </Button>
          </div>

          {/* Chat List */}
          <div className="flex-1 overflow-y-auto px-2 pb-4 hide-scrollbar">
            {filteredChats.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 opacity-40">
                <MessageCircle className="w-8 h-8 mb-2" />
                <p className="text-xs font-medium">
                  {searchQuery ? 'No matching chats' : 'No conversations yet'}
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                {filteredChats.map((tab) => (
                  <motion.div
                    key={tab.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className={cn(
                      "group relative px-3 py-2.5 rounded-lg cursor-pointer transition-all",
                      activeChatId === tab.id
                        ? 'bg-violet-500/15 border border-violet-500/30'
                        : 'hover:bg-muted/50 border border-transparent'
                    )}
                    onClick={() => {
                      if (editingChatId !== tab.id) {
                        switchChat(tab.id);
                        setShowChat(true);
                        // Close sidebar on mobile after selection
                        if (window.innerWidth < 768) {
                          setShowChatsPanel(false);
                        }
                      }
                    }}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        {editingChatId === tab.id ? (
                          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                            <Input
                              value={editingChatTitle}
                              onChange={(e) => setEditingChatTitle(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  renameChat(tab.id, editingChatTitle);
                                  setEditingChatId(null);
                                  toast.success('Chat renamed');
                                } else if (e.key === 'Escape') {
                                  setEditingChatId(null);
                                }
                              }}
                              className="h-6 text-xs bg-muted border-border focus:border-violet-500"
                              autoFocus
                            />
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label="Save chat name"
                              onClick={(e) => {
                                e.stopPropagation();
                                renameChat(tab.id, editingChatTitle);
                                setEditingChatId(null);
                                toast.success('Chat renamed');
                              }}
                              className="h-6 w-6 rounded hover:bg-green-500/20 hover:text-green-400"
                            >
                              <Check className="w-3 h-3" />
                            </Button>
                          </div>
                        ) : (
                          <>
                            <p className="font-medium text-sm truncate">{tab.title}</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">
                              {tab.messages.length} messages
                            </p>
                          </>
                        )}
                      </div>
                      {editingChatId !== tab.id && (
                        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label="Rename chat"
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingChatId(tab.id);
                              setEditingChatTitle(tab.title);
                            }}
                            className="h-6 w-6 rounded hover:bg-violet-500/20 hover:text-violet-400"
                          >
                            <Pencil className="w-3 h-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label="Delete chat"
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteChat(tab.id);
                            }}
                            className="h-6 w-6 rounded hover:bg-red-500/20 hover:text-red-400"
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </div>
      </motion.div>

      {/* Mobile Sidebar - Slides in from left */}
      <motion.div
        initial={false}
        animate={{ x: showChatsPanel ? 0 : '-100%' }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
        className="fixed md:hidden left-0 top-0 h-full z-50 w-[280px]"
      >
        <div className="w-full h-full glass border-r border-border flex flex-col bg-background">
          {/* Sidebar Header */}
          <div className="p-4 border-b border-border">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold font-display tracking-tight">Your Chats</h3>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Close sidebar"
                onClick={() => setShowChatsPanel(false)}
                className="h-8 w-8 rounded-lg hover:bg-accent"
              >
                <PanelLeftClose className="w-4 h-4" />
              </Button>
            </div>
            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search chats..."
                className="pl-9 h-9 bg-muted/50 border-border focus:border-violet-500"
              />
            </div>
          </div>
          {/* New Chat Button */}
          <div className="p-3">
            <Button
              onClick={handleNewChat}
              className="w-full h-10 bg-violet-600 hover:bg-violet-500 text-white rounded-lg font-semibold gap-2 transition-all"
            >
              <Plus className="w-4 h-4" />
              New Chat
            </Button>
          </div>
          {/* Chat List */}
          <div className="flex-1 overflow-y-auto px-2 pb-4 hide-scrollbar">
            {filteredChats.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 opacity-40">
                <MessageCircle className="w-8 h-8 mb-2" />
                <p className="text-xs font-medium">
                  {searchQuery ? 'No matching chats' : 'No conversations yet'}
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                {filteredChats.map((tab) => (
                  <div
                    key={tab.id}
                    className={cn(
                      "group relative px-3 py-2.5 rounded-lg cursor-pointer transition-all",
                      activeChatId === tab.id
                        ? 'bg-violet-500/15 border border-violet-500/30'
                        : 'hover:bg-muted/50 border border-transparent'
                    )}
                    onClick={() => {
                      if (editingChatId !== tab.id) {
                        switchChat(tab.id);
                        setShowChat(true);
                        setShowChatsPanel(false);
                      }
                    }}
                  >
                    <p className="font-medium text-sm truncate">{tab.title}</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                      {tab.messages.length} messages
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </motion.div>

      {/* Main Content - dynamically resizes */}
      <div className="flex-1 flex flex-col relative min-w-0">
        {/* Background */}
        <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
          <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] bg-violet-500/8 rounded-full blur-[150px]" />
          <div className="absolute bottom-[-20%] right-[-10%] w-[600px] h-[600px] bg-purple-500/5 rounded-full blur-[150px]" />
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-background/50 to-background" />
        </div>

        {/* Header - hidden in fullscreen voice mode for immersive experience */}
        {isFullscreenVoice && !showChat ? (
          /* Floating END button in fullscreen voice mode - red, abrupt stop */
          <div className="absolute top-4 right-4 z-30">
            <Button
              variant="destructive"
              size="sm"
              onClick={abruptEndVoiceMode}
              className="h-10 px-4 rounded-xl bg-red-600 hover:bg-red-700 text-white border-none shadow-lg shadow-red-500/20 transition-all"
            >
              <PhoneOff className="w-4 h-4 mr-2" />
              <span className="text-sm font-semibold">End</span>
            </Button>
          </div>
        ) : (
          <header className="relative z-20 flex items-center justify-between px-3 sm:px-6 py-3 sm:py-5">
            <div className="flex items-center gap-2 sm:gap-4">
              <Button
                variant="ghost"
                size="icon"
                aria-label={showChatsPanel ? "Close sidebar" : "Open sidebar"}
                onClick={() => setShowChatsPanel(!showChatsPanel)}
                className="h-9 w-9 sm:h-11 sm:w-11 rounded-xl glass border border-border hover:border-violet-500/30 hover:bg-accent transition-all"
              >
                {showChatsPanel ? (
                  <PanelLeftClose className="w-4 h-4 sm:w-5 sm:h-5 text-violet-400" />
                ) : (
                  <PanelLeft className="w-4 h-4 sm:w-5 sm:h-5 text-zinc-400" />
                )}
              </Button>
              {!showChatsPanel && chatTabs.length > 0 && (
                <span className="px-2 py-0.5 text-[10px] sm:text-xs font-bold bg-violet-500/20 text-violet-400 rounded-full hidden sm:inline">
                  {chatTabs.length} chats
                </span>
              )}
            </div>

          <div className="flex items-center gap-2 sm:gap-3">
            {/* Info Button - Shows dataset stats */}
            <DatasetInfoPopover
              datasetInfo={demoDatasetInfo || activeChat?.datasetStats || null}
              isConnected={isConnectionVerified}
            />

            <Button
              variant="ghost"
              onClick={() => {
                const newShowChat = !showChat;
                setShowChat(newShowChat);
                // Exit fullscreen voice mode when switching to chat
                if (newShowChat) {
                  setIsFullscreenVoice(false);
                }
              }}
              className={cn(
                "h-9 sm:h-11 px-2 sm:px-4 rounded-xl border transition-all gap-1.5 sm:gap-2",
                showChat
                  ? 'bg-violet-500 text-white border-violet-400 hover:bg-violet-400'
                  : 'glass border-border hover:border-violet-500/30 hover:bg-accent'
              )}
            >
              <MessageCircle className="w-4 h-4" />
              <span className="text-xs sm:text-sm font-medium">Chat</span>
            </Button>

            {/* Clear Chat Button - only visible when in chat mode with messages */}
            {showChat && messages.length > 0 && (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Clear chat conversation"
                    className="h-9 w-9 sm:h-11 sm:w-11 rounded-xl glass border border-border hover:border-red-500/30 hover:bg-red-500/10 transition-all"
                  >
                    <Eraser className="w-4 h-4 text-zinc-400" />
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent className="bg-card border-border">
                  <AlertDialogHeader>
                    <AlertDialogTitle>Clear conversation?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will delete all messages in this chat. Your dataset connection will be preserved.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel className="border-border hover:bg-accent">Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={() => {
                        clearCurrentChat();
                        toast.success("Chat cleared");
                      }}
                      className="bg-red-500 hover:bg-red-600 text-white"
                    >
                      Clear Chat
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="User menu"
                  className="h-9 w-9 sm:h-11 sm:w-11 rounded-xl glass border border-border hover:border-violet-500/30 hover:bg-accent transition-all"
                >
                  <User className="w-4 h-4 text-zinc-400" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56 bg-card border-border text-card-foreground">
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">{username}</p>
                    <p className="text-xs leading-none text-muted-foreground">Thara.ai User</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator className="bg-border" />
                <DropdownMenuItem
                  onClick={() => setShowSettings(true)}
                  className="cursor-pointer hover:bg-accent focus:bg-accent"
                >
                  <Settings className="mr-2 h-4 w-4" />
                  <span>Settings</span>
                </DropdownMenuItem>
                <DropdownMenuItem className="cursor-pointer hover:bg-accent focus:bg-accent">
                  <User className="mr-2 h-4 w-4" />
                  <span>Profile</span>
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-border" />
                <DropdownMenuItem
                  onClick={onLogout}
                  className="cursor-pointer text-red-400 hover:bg-accent focus:bg-accent hover:text-red-300"
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Logout</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          </header>
        )}

        {/* Settings Dialog */}
        <Dialog open={showSettings} onOpenChange={setShowSettings}>
          <DialogContent className="bg-card border-border text-card-foreground sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="text-xl font-display font-bold">Settings</DialogTitle>
            </DialogHeader>
            <div className="space-y-6 py-4">
              <div className="space-y-3">
                <label className="text-sm font-bold text-foreground">Theme</label>
                <div className="grid grid-cols-3 gap-3">
                  <button
                    onClick={() => setTheme('light')}
                    className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${theme === 'light'
                      ? 'border-violet-500 bg-violet-500/10'
                      : 'border-border hover:border-muted-foreground bg-muted'
                      }`}
                  >
                    <Sun className="w-5 h-5" />
                    <span className="text-xs font-medium">Light</span>
                  </button>
                  <button
                    onClick={() => setTheme('system')}
                    className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${theme === 'system'
                      ? 'border-violet-500 bg-violet-500/10'
                      : 'border-border hover:border-muted-foreground bg-muted'
                      }`}
                  >
                    <Monitor className="w-5 h-5" />
                    <span className="text-xs font-medium">System</span>
                  </button>
                  <button
                    onClick={() => setTheme('dark')}
                    className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${theme === 'dark'
                      ? 'border-violet-500 bg-violet-500/10'
                      : 'border-border hover:border-muted-foreground bg-muted'
                      }`}
                  >
                    <Moon className="w-5 h-5" />
                    <span className="text-xs font-medium">Dark</span>
                  </button>
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* Main Experience */}
        <main className="flex-1 relative flex items-center justify-center overflow-hidden">
          <AnimatePresence mode="wait">
            {!showChat ? (
              <motion.div
                key="voice"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 1.05 }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                className="relative z-10 w-full max-w-3xl flex flex-col items-center justify-between h-full py-4 sm:py-8 gap-2 sm:gap-4 px-4 sm:px-6 overflow-hidden"
              >
                <div className="flex-1 flex flex-col items-center justify-center gap-4 sm:gap-8 w-full min-h-0">
                  {/* Brand Header */}
                  <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="text-center space-y-2"
                  >
                    <h1 className="text-2xl sm:text-3xl md:text-4xl font-display font-bold tracking-tight">
                      {isRecording ? (
                        <span className="text-violet-400">Listening<span className="animate-pulse">...</span></span>
                      ) : (isProcessingVoice || isProcessingQuery) ? (
                        <span className="text-cyan-400">Processing<span className="animate-pulse">...</span></span>
                      ) : isSpeaking ? (
                        <span className="text-purple-400">Speaking<span className="animate-pulse">...</span></span>
                      ) : (
                        <>Hello <span className="gradient-text">{username}</span></>
                      )}
                    </h1>
                    <p className="text-zinc-500 text-xs sm:text-sm font-medium max-w-md mx-auto px-4">
                      {isRecording
                        ? "Voice captured securely"
                        : (isProcessingVoice || isProcessingQuery)
                          ? "Working on your request..."
                          : isSpeaking
                            ? "Tap to stop"
                            : "Tap to start voice conversation"}
                    </p>
                  </motion.div>

                  {/* Voice Visualizer - always show in voice mode */}
                  {/* Animate based on state: recording, speaking, or idle */}
                  <VoiceVisualizer
                    isRecording={isRecording}
                    isSpeaking={isSpeaking || isProcessingVoice || isProcessingQuery}
                  />

                  {/* Voice Button - supports push-to-talk on mobile */}
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    animate={isRecording ? {
                      scale: [1, 1.05, 1],
                    } : {}}
                    transition={isRecording ? {
                      duration: 1.5,
                      repeat: Infinity,
                      ease: "easeInOut"
                    } : {}}
                    onClick={() => {
                      // If speaking, stop TTS
                      if (isSpeaking) {
                        stopTextToSpeech();
                        return;
                      }
                      // Toggle recording on/off
                      handleVoiceToggle();
                    }}
                    aria-label={isRecording ? "Tap to stop recording" : isSpeaking ? "Stop speaking" : "Tap to start recording"}
                    className={`relative w-14 h-14 sm:w-16 sm:h-16 rounded-full transition-all duration-500 flex items-center justify-center ${
                      isRecording
                        ? 'bg-violet-500 shadow-[0_0_60px_rgba(139,92,246,0.5)]'
                        : isSpeaking
                          ? 'bg-red-500 shadow-[0_0_60px_rgba(239,68,68,0.5)]'
                          : (isProcessingVoice || isProcessingQuery)
                            ? 'bg-cyan-500/20 border-2 border-cyan-500 shadow-[0_0_40px_rgba(6,182,212,0.3)]'
                            : 'bg-secondary border border-border hover:border-primary/50 hover:shadow-[0_0_40px_rgba(var(--primary),0.2)]'
                      }`}
                  >
                    {/* Pulsing ring when recording */}
                    {isRecording && (
                      <motion.span
                        className="absolute inset-0 rounded-full bg-violet-500"
                        animate={{
                          scale: [1, 1.5],
                          opacity: [0.4, 0]
                        }}
                        transition={{
                          duration: 1.2,
                          repeat: Infinity,
                          ease: "easeOut"
                        }}
                      />
                    )}
                    {/* Pulsing ring when speaking */}
                    {isSpeaking && (
                      <motion.span
                        className="absolute inset-0 rounded-full bg-red-500"
                        animate={{
                          scale: [1, 1.5],
                          opacity: [0.4, 0]
                        }}
                        transition={{
                          duration: 1.2,
                          repeat: Infinity,
                          ease: "easeOut"
                        }}
                      />
                    )}
                    {/* Pulsing ring when processing */}
                    {(isProcessingVoice || isProcessingQuery) && !isRecording && !isSpeaking && (
                      <motion.span
                        className="absolute inset-0 rounded-full border-2 border-cyan-500"
                        animate={{
                          scale: [1, 1.3],
                          opacity: [0.6, 0]
                        }}
                        transition={{
                          duration: 1.5,
                          repeat: Infinity,
                          ease: "easeOut"
                        }}
                      />
                    )}
                    <AnimatePresence mode="wait">
                      {isSpeaking ? (
                        <motion.div
                          key="stop-speaking"
                          initial={{ scale: 0, rotate: -90 }}
                          animate={{ scale: 1, rotate: 0 }}
                          exit={{ scale: 0, rotate: 90 }}
                        >
                          <StopCircle className="w-6 h-6 text-white" />
                        </motion.div>
                      ) : isRecording ? (
                        <motion.div
                          key="stop"
                          initial={{ scale: 0, rotate: -90 }}
                          animate={{ scale: 1, rotate: 0 }}
                          exit={{ scale: 0, rotate: 90 }}
                        >
                          <Square className="w-6 h-6 text-white fill-current" />
                        </motion.div>
                      ) : isProcessingVoice ? (
                        <motion.div
                          key="loading"
                          initial={{ scale: 0, rotate: 90 }}
                          animate={{ scale: 1, rotate: 0 }}
                          exit={{ scale: 0, rotate: -90 }}
                        >
                          <Loader2 className="w-8 h-8 text-primary animate-spin" />
                        </motion.div>
                      ) : (
                        <motion.div
                          key="mic"
                          initial={{ scale: 0, rotate: 90 }}
                          animate={{ scale: 1, rotate: 0 }}
                          exit={{ scale: 0, rotate: -90 }}
                        >
                          <Mic className="w-6 h-6 text-muted-foreground" />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.button>
                </div>

                {/* Animated Suggestion Pill */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className="w-full max-w-xl mx-auto px-4"
                >
                  <TypingPlaceholderPill
                    suggestions={[
                      "Which month recorded the highest total profit?",
                      "Are sales increasing or decreasing in Chennai?",
                      "Which category shows consistent growth?",
                      "How many transactions were made using UPI?"
                    ]}
                    onSelect={(suggestion) => {
                      setInputMessage(suggestion);
                      setShowChat(true);
                    }}
                  />
                </motion.div>

              </motion.div>
            ) : (
              <motion.div
                key="chat"
                initial={{ opacity: 0, x: 50 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -50 }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                className="absolute inset-0 z-20 flex flex-col pt-2 sm:pt-4"
              >
                <div className="max-w-4xl mx-auto w-full flex flex-col h-full px-3 sm:px-6">
                  <div className="flex items-center justify-between mb-3 sm:mb-6">
                    <div>
                      <h2 className="text-xl sm:text-2xl font-display font-bold">Chat</h2>
                      <p className="text-zinc-500 text-xs sm:text-sm">Conversation with Thara</p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setShowChat(false)}
                      className="h-9 w-9 sm:h-10 sm:w-10 rounded-xl glass border border-zinc-800/50 hover:border-violet-500/30"
                    >
                      <ChevronLeft className="w-4 h-4 sm:w-5 sm:h-5" />
                    </Button>
                  </div>

                  <div
                    ref={scrollRef}
                    className="flex-1 overflow-y-auto space-y-4 sm:space-y-6 pb-20 sm:pb-24 hide-scrollbar"
                  >
                    {messages.length === 0 ? (
                      <div className="h-full flex flex-col items-center justify-center py-12">
                        <div className="text-center space-y-4">
                          <div className="w-16 h-16 mx-auto rounded-2xl bg-violet-500/10 flex items-center justify-center">
                            <MessageCircle className="w-8 h-8 text-violet-500" />
                          </div>
                          <div className="space-y-2">
                            <h3 className="text-lg font-semibold text-foreground">Start a conversation</h3>
                            <p className="text-sm text-muted-foreground max-w-sm">
                              Ask questions about your data using voice or text
                            </p>
                          </div>
                          <div className="mt-6 space-y-2">
                            <p className="text-xs text-muted-foreground uppercase tracking-wider">Try asking</p>
                            <div className="flex flex-wrap justify-center gap-2">
                              {["How many transactions used UPI?", "Which month had highest profit?", "Show month-over-month growth"].map((suggestion) => (
                                <button
                                  key={suggestion}
                                  onClick={() => {
                                    setInputMessage(suggestion);
                                  }}
                                  className="px-3 py-1.5 text-xs rounded-full bg-muted hover:bg-accent border border-border hover:border-violet-500/30 transition-all"
                                >
                                  {suggestion}
                                </button>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <>
                        {messages.map((msg) => (
                          <MessageBubble
                            key={msg.id}
                            message={{ ...msg, isSpeaking: speakingMessageId === msg.id }}
                            onPlay={playTextToSpeech}
                            onStop={stopTextToSpeech}
                          />
                        ))}
                        {/* Follow-up suggestions after assistant response */}
                        {messages.length > 0 && messages[messages.length - 1].role === 'assistant' && !isProcessingQuery && !isProcessingVoice && (
                          <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="mt-4 space-y-2"
                          >
                            <p className="text-xs text-muted-foreground uppercase tracking-wider">Try asking</p>
                            <div className="flex flex-wrap gap-2">
                              {followUpSuggestions.map((suggestion) => (
                                <button
                                  key={suggestion}
                                  onClick={() => {
                                    setInputMessage(suggestion);
                                  }}
                                  className="px-3 py-1.5 text-xs rounded-full bg-muted hover:bg-accent border border-border hover:border-violet-500/30 transition-all text-left"
                                >
                                  {suggestion}
                                </button>
                              ))}
                            </div>
                          </motion.div>
                        )}
                      </>
                    )}
                    {/* Show processing status while waiting for response */}
                    <AnimatePresence>
                      {(isProcessingVoice || isProcessingQuery) && (
                        <ProcessingStatus
                          isProcessing={true}
                          isVoiceInput={isCurrentInputVoice}
                          hasTamilInput={hasTamilInput}
                          variant="chat"
                        />
                      )}
                    </AnimatePresence>
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
                </div>

                {/* Input Box with Voice and Send */}
                <div className="absolute bottom-3 sm:bottom-6 left-0 right-0 px-3 sm:px-6 pointer-events-none">
                  <div className="max-w-4xl mx-auto pointer-events-auto">
                    <div className="flex items-center gap-1.5 sm:gap-2 p-1.5 sm:p-2 rounded-xl sm:rounded-2xl glass border border-border bg-card/80 backdrop-blur-xl">
                      <Input
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyPress={(e) => {
                          if (e.key === 'Enter' && inputMessage.trim()) {
                            handleSendMessage(inputMessage);
                            setInputMessage('');
                          }
                        }}
                        placeholder="Type your message..."
                        className="flex-1 bg-transparent border-0 focus-visible:ring-0 focus-visible:ring-offset-0 text-sm sm:text-base text-foreground placeholder:text-muted-foreground"
                      />
                      {/* Single Mic Button - Click to enable voice & record, or stop recording */}
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        animate={isRecording ? {
                          scale: [1, 1.1, 1],
                          boxShadow: [
                            '0 0 0 0 rgba(139, 92, 246, 0.4)',
                            '0 0 0 10px rgba(139, 92, 246, 0)',
                            '0 0 0 0 rgba(139, 92, 246, 0)'
                          ]
                        } : {}}
                        transition={isRecording ? {
                          duration: 1.2,
                          repeat: Infinity,
                          ease: "easeInOut"
                        } : {}}
                        onClick={() => {
                          if (!isVoiceEnabledInChat) {
                            // Enable voice and start recording
                            setIsVoiceEnabledInChat(true);
                          }
                          handleVoiceToggle();
                        }}
                        aria-label={isRecording ? "Stop recording" : "Start recording"}
                        className={cn(
                          "w-9 h-9 sm:w-10 sm:h-10 rounded-lg sm:rounded-xl transition-all duration-300 flex items-center justify-center flex-shrink-0 relative",
                          isRecording
                            ? 'bg-violet-500 shadow-[0_0_30px_rgba(139,92,246,0.6)]'
                            : 'bg-secondary border border-border hover:border-primary/50'
                        )}
                      >
                        {/* Pulsing ring when recording */}
                        {isRecording && (
                          <motion.span
                            className="absolute inset-0 rounded-lg sm:rounded-xl bg-violet-500"
                            animate={{
                              scale: [1, 1.4],
                              opacity: [0.5, 0]
                            }}
                            transition={{
                              duration: 1,
                              repeat: Infinity,
                              ease: "easeOut"
                            }}
                          />
                        )}
                        <AnimatePresence mode="wait">
                          {isRecording ? (
                            <motion.div
                              key="recording-stop"
                              initial={{ scale: 0, rotate: -90 }}
                              animate={{ scale: 1, rotate: 0 }}
                              exit={{ scale: 0, rotate: 90 }}
                              transition={{ duration: 0.2 }}
                            >
                              <Square className="w-4 h-4 sm:w-5 sm:h-5 text-white fill-current" />
                            </motion.div>
                          ) : (
                            <motion.div
                              key="mic-idle"
                              initial={{ scale: 0, rotate: 90 }}
                              animate={{ scale: 1, rotate: 0 }}
                              exit={{ scale: 0, rotate: -90 }}
                              transition={{ duration: 0.2 }}
                            >
                              <Mic className="w-4 h-4 sm:w-5 sm:h-5 text-muted-foreground" />
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </motion.button>
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => {
                          if (inputMessage.trim()) {
                            handleSendMessage(inputMessage);
                            setInputMessage('');
                          }
                        }}
                        disabled={!inputMessage.trim()}
                        aria-label="Send message"
                        className={cn(
                          "w-9 h-9 sm:w-10 sm:h-10 rounded-lg sm:rounded-xl transition-all duration-300 flex items-center justify-center flex-shrink-0",
                          inputMessage.trim()
                            ? 'bg-primary hover:bg-primary/90 shadow-[0_0_20px_rgba(var(--primary),0.3)]'
                            : 'bg-secondary border border-border opacity-50 cursor-not-allowed'
                        )}
                      >
                        <Send className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                      </motion.button>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
