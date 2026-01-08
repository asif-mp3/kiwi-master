'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppState } from '@/lib/hooks';
import { MessageBubble } from './MessageBubble';
import { MessageSkeleton } from './MessageSkeleton';
import { VoiceVisualizer } from './VoiceVisualizer';
import { api } from '@/services/api';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  LogOut,
  Mic,
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
  PanelLeft
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
import { DatasetConnection, DatasetStats } from './DatasetConnection';
import { VOICE_RECORDING_TIMEOUT, VOICE_MODE_TIMEOUT } from '@/lib/constants';

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
      <div className="flex items-center gap-3 h-14 px-6 rounded-full bg-zinc-900/80 border border-zinc-700/50 hover:border-violet-500/50 hover:bg-zinc-800/80 transition-all duration-300 backdrop-blur-xl shadow-lg shadow-black/20">
        <Sparkles className="w-5 h-5 text-violet-400 shrink-0" />
        <div className="flex-1 overflow-hidden">
          <span className="text-zinc-400 text-sm font-medium">
            {displayText}
            <motion.span
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.5, repeat: Infinity, repeatType: "reverse" }}
              className="inline-block w-0.5 h-4 bg-violet-400 ml-0.5 align-middle"
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

export function ChatScreen({ onLogout, username }: ChatScreenProps) {
  const {
    messages,
    addMessage,
    config,
    chatTabs,
    activeChatId,
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
  const [isDatasetModalOpen, setIsDatasetModalOpen] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { theme, setTheme } = useTheme();

  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [audioChunks, setAudioChunks] = useState<Blob[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [editingChatTitle, setEditingChatTitle] = useState('');

  // Audio ref to control TTS playback (stop functionality)
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Track which message is currently speaking
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);

  // Timeout refs for cleanup (prevent memory leaks)
  const voiceModeTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const recordingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  /* New State for Voice Section Toggles - REMOVED, replaced with suggestion UI */
  const [expandedVoiceSection, setExpandedVoiceSection] = useState<'plan' | 'data' | 'schema' | null>(null);

  // Search state for sidebar
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, showChat]);

  // Cleanup timeouts on unmount to prevent memory leaks
  useEffect(() => {
    return () => {
      if (voiceModeTimeoutRef.current) {
        clearTimeout(voiceModeTimeoutRef.current);
      }
      if (recordingTimeoutRef.current) {
        clearTimeout(recordingTimeoutRef.current);
      }
    };
  }, []);

  // Push-to-talk: Track if recording was started via push-to-talk
  const isPushToTalkRef = useRef(false);

  // Ref to hold the latest handleVoiceToggle function (avoids stale closure in useEffect)
  const handleVoiceToggleRef = useRef<() => void>(() => {});

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
    } else {
      // No dataset connected - reset verification state (be honest)
      setIsConnectionVerified(false);
    }
  }, [activeChat?.datasetStatus, activeChat?.datasetUrl]);

  const handleSendMessage = async (content: string, shouldPlayTTS: boolean = false) => {
    if (!activeChatId) {
      createNewChat();
    }

    // Check for dataset connection
    const currentChat = activeChatId ? chatTabs.find(t => t.id === activeChatId) : null;
    if (!currentChat || currentChat.datasetStatus !== 'ready') {
      setIsDatasetModalOpen(true);
      toast.error("Dataset Required", { description: "Please connect a Google Sheet to continue." });
      return;
    }

    addMessage(content, 'user');

    // Call API with delay
    try {
      const response = await api.sendMessage(content);

      if (response.success) {
        addMessage(response.explanation, 'assistant', {
          plan: response.plan,
          data: response.data,
          schema_context: response.schema_context,
          data_refreshed: response.data_refreshed
        });

        // Auto-expand Query Plan if available
        if (response.plan) {
          setExpandedVoiceSection('plan');
        }

        // Play TTS response with Rachel voice
        console.log('🔊 shouldPlayTTS:', shouldPlayTTS);
        console.log('📝 Response explanation:', response.explanation.substring(0, 50));

        if (shouldPlayTTS) {
          console.log('✅ Playing TTS (flag enabled)...');
          await playTextToSpeech(response.explanation);
        } else {
          console.log('⚠️ TTS disabled (flag not set)');
        }

      } else {
        // Use explanation (user-friendly) with fallback to error message
        const errorMsg = response.explanation || response.error || "Sorry, I encountered an error extracting that information.";
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

      setIsSpeaking(true);
      setSpeakingMessageId(messageId || null);
      console.log('🔊 Playing TTS for:', text.substring(0, 50) + '...');

      // Call TTS endpoint via API service
      const audioBlob = await api.textToSpeech(text);
      console.log('✅ Received audio blob:', audioBlob.size, 'bytes');

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
      };

      audio.onerror = (e) => {
        console.error('❌ Audio playback error:', e);
        setIsSpeaking(false);
        setSpeakingMessageId(null);
        audioRef.current = null;
        URL.revokeObjectURL(audioUrl);
      };

      await audio.play();
      audio.playbackRate = 1.3;  // 50% faster playback
      console.log('▶️ TTS playback started at 1.5x speed');

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

  // Sync dataset changes
  const handleSyncDataset = async () => {
    if (!activeChat?.datasetUrl || isSyncing) return;

    setIsSyncing(true);
    try {
      console.log('[Sync] Refreshing dataset...');
      const response = await api.loadDataset(activeChat.datasetUrl);
      if (response.success && response.stats) {
        // Update the chat's dataset stats
        setDatasetForChat(activeChat.datasetUrl, 'ready', response.stats);
        toast.success("Data synced", {
          description: `${response.stats.totalTables} tables, ${response.stats.totalRecords?.toLocaleString()} records`
        });
      }
    } catch (error) {
      console.error('[Sync] Failed:', error);
      toast.error("Sync failed", { description: "Could not refresh data" });
    } finally {
      setIsSyncing(false);
    }
  };

  const handleVoiceToggle = async () => {
    if (!activeChat) {
      // Trigger new chat or mandatory dataset prompt
      if (!isDatasetModalOpen) setIsDatasetModalOpen(true);
      return;
    }

    if (!activeChat.datasetUrl) {
      toast.error("Please connect a dataset first", {
        description: "Thara needs data to answer your questions."
      });
      setIsDatasetModalOpen(true);
      return;
    }

    const newIsRecording = !isRecording;
    setIsRecording(newIsRecording);

    if (newIsRecording) { // Started listening
      console.log('🎤 Started listening...');
      setExpandedVoiceSection(null);

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

          // Stop all tracks
          stream.getTracks().forEach(track => track.stop());

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

            // Enable voice mode for TTS playback
            console.log('🔊 Enabling voice mode for TTS...');
            setIsVoiceMode(true);

            // Send transcribed message WITH TTS enabled
            console.log('📤 Sending transcribed message with TTS...');
            await handleSendMessage(text, true); // Pass true to enable TTS
            setIsProcessingVoice(false); // Stop loading UI

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

        // Auto-stop after timeout
        // Clear any previous timeout before setting a new one
        if (recordingTimeoutRef.current) {
          clearTimeout(recordingTimeoutRef.current);
        }
        recordingTimeoutRef.current = setTimeout(() => {
          if (recorder.state === 'recording') {
            console.log('⏱️ Auto-stopping after timeout...');
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
      }

    } else {
      // Manual stop
      console.log('🛑 Manually stopping recording...');
      // Clear the auto-stop timeout since we're manually stopping
      if (recordingTimeoutRef.current) {
        clearTimeout(recordingTimeoutRef.current);
        recordingTimeoutRef.current = null;
      }
      if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
      }
    }
  };

  // Keep the ref updated with the latest handleVoiceToggle function
  useEffect(() => {
    handleVoiceToggleRef.current = handleVoiceToggle;
  });

  // Push-to-talk: Shift key hold to record (desktop)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only trigger if Shift is pressed, not already recording, and not typing in an input
      if (e.key === 'Shift' && !isRecording && !isPushToTalkRef.current) {
        const activeElement = document.activeElement;
        const isTyping = activeElement?.tagName === 'INPUT' || activeElement?.tagName === 'TEXTAREA';
        if (!isTyping) {
          isPushToTalkRef.current = true;
          handleVoiceToggleRef.current();
        }
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      // Stop recording when Shift is released (only if started via push-to-talk)
      if (e.key === 'Shift' && isPushToTalkRef.current && isRecording) {
        isPushToTalkRef.current = false;
        handleVoiceToggleRef.current();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [isRecording]);

  const handleDatasetSuccess = (url: string, stats: DatasetStats) => {
    console.log('[ChatScreen] Dataset connected with stats:', stats);

    // Ensure a chat exists before connecting dataset
    let chatIdToUse = activeChatId;
    if (!chatIdToUse) {
      console.log('[ChatScreen] No active chat, creating one for dataset connection');
      const newChat = createNewChat();
      chatIdToUse = newChat.id;
    }

    // Update the chat with dataset info (passing chatId explicitly)
    setDatasetForChat(url, 'ready', {
      totalTables: stats.totalTables,
      totalRecords: stats.totalRecords,
      sheetCount: stats.sheetCount,
      sheets: stats.sheets,
      detectedTables: stats.detectedTables
    }, chatIdToUse);

    // Dataset just loaded successfully - mark as verified immediately (no need to re-verify)
    setIsConnectionVerified(true);
    hasVerifiedOnce.current = true; // Prevent useEffect from re-verifying
    setIsDatasetModalOpen(false);
    toast.success("Dataset Connected & Locked", {
      description: `${stats.sheetCount} sheets with ${stats.totalTables} tables loaded.`
    });
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
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
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

        {/* Header */}
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
            {/* Dataset Button - shows honest state */}
            <Button
              variant="ghost"
              onClick={() => setIsDatasetModalOpen(true)}
              className={cn(
                "h-9 sm:h-11 px-2 sm:px-4 rounded-xl glass border transition-all gap-1.5 sm:gap-2",
                activeChat?.datasetStatus === 'ready' && isConnectionVerified
                  ? "border-violet-500/50 bg-violet-500/10 text-violet-400 hover:bg-violet-500/20"
                  : "border-border hover:border-violet-500/30 hover:bg-accent"
              )}
            >
              <Table className={cn("w-4 h-4", activeChat?.datasetStatus === 'ready' && isConnectionVerified ? "text-violet-400" : "text-zinc-400")} />
              <span className="text-xs sm:text-sm font-medium hidden sm:inline">
                {activeChat?.datasetStatus === 'ready' && isConnectionVerified
                  ? 'Connected'
                  : 'Connect Data'}
              </span>
            </Button>

            {/* Sync Button - Only show when dataset is connected */}
            {activeChat?.datasetStatus === 'ready' && isConnectionVerified && (
              <Button
                variant="ghost"
                size="icon"
                onClick={handleSyncDataset}
                disabled={isSyncing}
                aria-label="Sync dataset"
                className="h-9 w-9 sm:h-11 sm:w-11 rounded-xl glass border border-emerald-500/30 hover:border-emerald-500/50 hover:bg-emerald-500/10 transition-all"
              >
                <RefreshCw className={cn("w-4 h-4 text-emerald-400", isSyncing && "animate-spin")} />
              </Button>
            )}

            <DatasetConnection
              isOpen={isDatasetModalOpen}
              onClose={() => setIsDatasetModalOpen(false)}
              onSuccess={handleDatasetSuccess}
              initialUrl={activeChat?.datasetUrl || ''}
              isLocked={activeChat?.datasetStatus === 'ready'}
              isConnectionVerified={isConnectionVerified}
              initialStats={activeChat?.datasetStats}
            />

            <Button
              variant="ghost"
              onClick={() => setShowChat(!showChat)}
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
                className="relative z-10 w-full max-w-3xl flex flex-col items-center justify-between h-full py-8 gap-4 px-6"
              >
                <div className="flex-1 flex flex-col items-center justify-center gap-8 w-full">
                  {/* Brand Header */}
                  <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="text-center space-y-2"
                  >
                    <h1 className="text-4xl font-display font-bold tracking-tight">
                      {isRecording ? (
                        <span className="text-violet-400">Listening<span className="animate-pulse">...</span></span>
                      ) : isSpeaking ? (
                        <span className="text-purple-400">Speaking<span className="animate-pulse">...</span></span>
                      ) : (
                        <>Hey, <span className="gradient-text">{username}</span></>
                      )}
                    </h1>
                    <p className="text-zinc-500 text-sm font-medium max-w-md mx-auto">
                      {isRecording
                        ? "Your voice is being captured securely"
                        : isProcessingVoice
                          ? "Processing your request..."
                          : isSpeaking
                            ? "Speaking... tap the button to stop"
                            : "Tap the button below to start a voice conversation"}
                    </p>
                  </motion.div>

                  {/* Voice Visualizer */}
                  <VoiceVisualizer isRecording={isRecording} isSpeaking={isSpeaking} />

                  {/* Voice Button - supports push-to-talk on mobile */}
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={isSpeaking ? stopTextToSpeech : undefined}
                    onPointerDown={(e) => {
                      if (isSpeaking) return;
                      // Start recording on touch/hold
                      if (!isRecording) {
                        isPushToTalkRef.current = true;
                        handleVoiceToggle();
                      }
                    }}
                    onPointerUp={() => {
                      // Stop recording on release (only if push-to-talk)
                      if (isPushToTalkRef.current && isRecording) {
                        isPushToTalkRef.current = false;
                        handleVoiceToggle();
                      }
                    }}
                    onPointerLeave={() => {
                      // Stop if finger/cursor leaves the button while recording
                      if (isPushToTalkRef.current && isRecording) {
                        isPushToTalkRef.current = false;
                        handleVoiceToggle();
                      }
                    }}
                    aria-label={isRecording ? "Release to stop recording" : isSpeaking ? "Stop speaking" : "Hold to record"}
                    className={`relative w-16 h-16 rounded-full transition-all duration-500 flex items-center justify-center touch-none ${
                      isRecording
                        ? 'bg-violet-500 shadow-[0_0_60px_rgba(139,92,246,0.5)]'
                        : isSpeaking
                          ? 'bg-red-500 shadow-[0_0_60px_rgba(239,68,68,0.5)]'
                          : 'bg-secondary border border-border hover:border-primary/50 hover:shadow-[0_0_40px_rgba(var(--primary),0.2)]'
                      }`}
                  >
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
                      "What were the total sales last month?",
                      "Compare October vs November revenue",
                      "Show me top selling products",
                      "How much profit did we make this week?"
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
                              {activeChat?.datasetStatus === 'ready'
                                ? "Ask questions about your data using voice or text"
                                : "Connect a dataset first, then ask questions about your data"}
                            </p>
                          </div>
                          {activeChat?.datasetStatus !== 'ready' && (
                            <Button
                              variant="outline"
                              onClick={() => setIsDatasetModalOpen(true)}
                              className="mt-4 gap-2"
                            >
                              <Table className="w-4 h-4" />
                              Connect Dataset
                            </Button>
                          )}
                          {activeChat?.datasetStatus === 'ready' && (
                            <div className="mt-6 space-y-2">
                              <p className="text-xs text-muted-foreground uppercase tracking-wider">Try asking</p>
                              <div className="flex flex-wrap justify-center gap-2">
                                {["Show me total sales", "What are the top 5 items?", "Compare categories"].map((suggestion) => (
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
                          )}
                        </div>
                      </div>
                    ) : (
                      messages.map((msg) => (
                        <MessageBubble
                          key={msg.id}
                          message={{ ...msg, isSpeaking: speakingMessageId === msg.id }}
                          onPlay={playTextToSpeech}
                          onStop={stopTextToSpeech}
                        />
                      ))
                    )}
                    {/* Show skeleton while processing voice or waiting for response */}
                    {isProcessingVoice && (
                      <MessageSkeleton />
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
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onPointerDown={() => {
                          // Start recording on touch/hold
                          if (!isRecording) {
                            isPushToTalkRef.current = true;
                            handleVoiceToggle();
                          }
                        }}
                        onPointerUp={() => {
                          // Stop recording on release (only if push-to-talk)
                          if (isPushToTalkRef.current && isRecording) {
                            isPushToTalkRef.current = false;
                            handleVoiceToggle();
                          }
                        }}
                        onPointerLeave={() => {
                          // Stop if finger/cursor leaves the button while recording
                          if (isPushToTalkRef.current && isRecording) {
                            isPushToTalkRef.current = false;
                            handleVoiceToggle();
                          }
                        }}
                        aria-label={isRecording ? "Release to stop recording" : "Hold to record"}
                        className={cn(
                          "w-9 h-9 sm:w-10 sm:h-10 rounded-lg sm:rounded-xl transition-all duration-300 flex items-center justify-center flex-shrink-0 touch-none",
                          isRecording
                            ? 'bg-violet-500 shadow-[0_0_30px_rgba(139,92,246,0.5)]'
                            : 'bg-secondary border border-border hover:border-primary/50'
                        )}
                      >
                        {isRecording ? (
                          <Square className="w-4 h-4 sm:w-5 sm:h-5 text-white fill-current" />
                        ) : (
                          <Mic className="w-4 h-4 sm:w-5 sm:h-5 text-muted-foreground" />
                        )}
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
