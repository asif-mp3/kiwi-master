'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppState } from '@/lib/hooks';
import { MessageBubble } from './MessageBubble';
import { VoiceVisualizer } from './VoiceVisualizer';
import { ProcessingStatus } from './ProcessingStatus';
import { api } from '@/services/api';
import { getApiBaseUrl } from '@/lib/constants';
import { DataLoadingOverlay, LoadingStatus } from './DataLoadingOverlay';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  LogOut,
  Mic,
  Square,
  MessageCircle,
  ChevronLeft,
  Settings,
  User,
  Send,
  Sun,
  Moon,
  Monitor,
  Loader2,
  StopCircle,
  Eraser,
  PanelLeftClose,
  PanelLeft,
  PhoneOff,
} from 'lucide-react';
import { toast } from 'sonner';
import { useTheme } from 'next-themes';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
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
import { DatasetInfoPopover, DatasetInfo } from './DatasetInfoPopover';
import { DataSourcesPanel } from './DataSourcesPanel';
import { VoiceModeInput } from './VoiceModeInput';
import { LiveCaptions, MobileCaptions } from './LiveCaptions';
import { ChatSidebar } from './ChatSidebar';
import { getRandomSuggestions } from '@/config/suggestions';
import { useVoice } from '@/hooks/useVoice';

interface ChatScreenProps {
  onLogout: () => void;
  username: string;
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
    clearCurrentChat,
    sessionName,
    setSessionName
  } = useAppState();

  // ===== UI State =====
  const [showChat, setShowChat] = useState(false);
  const [showChatsPanel, setShowChatsPanel] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { theme, setTheme } = useTheme();

  // Track if we have verified the connection with the backend
  const [isConnectionVerified, setIsConnectionVerified] = useState(false);

  // Processing status tracking for UI feedback
  const [isProcessingQuery, setIsProcessingQuery] = useState(false);
  const [isCurrentInputVoice, setIsCurrentInputVoice] = useState(false);
  const [hasTamilInput, setHasTamilInput] = useState(false);

  // Demo mode state
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [demoDatasetInfo, setDemoDatasetInfo] = useState<DatasetInfo | null>(null);

  // Data Sources Panel state
  const [isDataSourcesPanelOpen, setIsDataSourcesPanelOpen] = useState(false);

  // Follow-up suggestions state
  const [followUpSuggestions, setFollowUpSuggestions] = useState<string[]>(() => getRandomSuggestions());

  // Live caption state for voice mode UI
  const [liveCaption, setLiveCaption] = useState<{ text: string; type: 'user' | 'assistant' | 'status' } | null>(null);

  // Track last visualization for right panel display
  const [lastVisualization, setLastVisualization] = useState<any>(null);

  // Voice section toggle (set when plan is available)
  const [expandedVoiceSection, setExpandedVoiceSection] = useState<'plan' | 'data' | 'schema' | null>(null);

  // Data loading overlay state (Phase 2: SSE progress)
  const [loadingStatus, setLoadingStatus] = useState<LoadingStatus>({
    phase: 'idle', message: '', progress: 0, tables_found: 0,
    tables_profiled: 0, total_tables: 0, complete: false, error: null,
  });
  const [showLoadingOverlay, setShowLoadingOverlay] = useState(false);

  // Smart suggestions from loaded data profiles
  const [smartSuggestions, setSmartSuggestions] = useState<string[]>([]);

  // ===== Voice Hook =====
  // Ref to break circular dependency: handleSendMessage ↔ voice.playTextToSpeech
  const sendMessageRef = useRef<(content: string, shouldPlayTTS: boolean, isVoiceInput: boolean) => Promise<void>>(undefined);

  const activeChat = getCurrentChat();

  const voice = useVoice({
    isConnectionVerified,
    activeChat: activeChat ? { id: activeChat.id } : null,
    isInChatView: showChat,
    addMessage,
    sendMessage: (content, shouldPlayTTS, isVoiceInput) =>
      sendMessageRef.current?.(content, shouldPlayTTS, isVoiceInput) ?? Promise.resolve(),
    setLiveCaption,
    setExpandedVoiceSection,
    setIsProcessingQuery,
    setIsCurrentInputVoice,
    setHasTamilInput,
  });

  // ===== Effects =====

  // SSE: Subscribe to loading progress from backend
  useEffect(() => {
    if (isConnectionVerified) return; // Already have data, no need to watch

    const apiBase = getApiBaseUrl();
    let eventSource: EventSource | null = null;

    try {
      eventSource = new EventSource(`${apiBase}/api/loading-progress`);
      eventSource.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as LoadingStatus;
          setLoadingStatus(data);

          // Show overlay when loading starts
          if (data.phase !== 'idle') {
            setShowLoadingOverlay(true);
          }

          // When ready, mark connection as verified and auto-dismiss after delay
          if (data.phase === 'ready' || data.complete) {
            setIsConnectionVerified(true);
            hasVerifiedOnce.current = true;
            setTimeout(() => setShowLoadingOverlay(false), 3000);
            eventSource?.close();
          }

          if (data.phase === 'error') {
            setTimeout(() => setShowLoadingOverlay(false), 10000);
            eventSource?.close();
          }
        } catch {
          // Ignore parse errors
        }
      };
      eventSource.onerror = () => {
        // SSE failed — fall back to polling via checkDemoMode
        eventSource?.close();
      };
    } catch {
      // EventSource not supported or URL issue
    }

    return () => {
      eventSource?.close();
    };
  }, [isConnectionVerified]);

  // Scroll to bottom when messages change
  useEffect(() => {
    const scrollToBottom = () => {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    };
    requestAnimationFrame(scrollToBottom);
    const t1 = setTimeout(scrollToBottom, 150);
    return () => {
      clearTimeout(t1);
    };
  }, [messages.length, showChat, activeChatId]);

  // Track if this is the initial mount (for verification logic)
  const hasVerifiedOnce = useRef(false);

  // Check if dataset was previously connected
  useEffect(() => {
    if (activeChat?.datasetStatus === 'ready' && activeChat?.datasetUrl) {
      setIsConnectionVerified(true);
      hasVerifiedOnce.current = true;
    } else if (!isDemoMode) {
      setIsConnectionVerified(false);
    }
  }, [activeChat?.datasetStatus, activeChat?.datasetUrl, isDemoMode]);

  // Check for demo mode (pre-loaded dataset) on mount
  useEffect(() => {
    const checkDemoMode = async () => {
      try {
        const response = await api.getDatasetStatus();
        if (response.loaded && response.demo_mode) {
          setIsConnectionVerified(true);
          hasVerifiedOnce.current = true;

          setIsDemoMode(true);
          const demoInfo: DatasetInfo = {
            totalTables: response.total_tables || 0,
            totalRecords: response.total_records || 0,
            sheetCount: response.original_sheets?.length || response.tables?.length || 2,
            sheets: response.original_sheets || [],
            detectedTables: response.detected_tables || [],
            tableProfiles: response.table_profiles_summary || [],
            sourceType: response.source_type || 'demo',
            smartSuggestions: response.smart_suggestions || [],
          };
          setDemoDatasetInfo(demoInfo);
          if (response.smart_suggestions?.length) {
            setSmartSuggestions(response.smart_suggestions);
          }

          if (chatTabs.length === 0) {
            createNewChat();
          }

          const demoStats = {
            totalTables: demoInfo.totalTables,
            totalRecords: demoInfo.totalRecords,
            sheetCount: demoInfo.sheetCount,
            sheets: demoInfo.sheets,
            detectedTables: demoInfo.detectedTables || []
          };

          chatTabs.forEach(chat => {
            if (chat.datasetStatus !== 'ready') {
              setDatasetForChat('demo://preloaded', 'ready', demoStats, chat.id);
            }
          });
        }
      } catch {
        setIsDemoMode(false);
      }
    };

    if (!hasVerifiedOnce.current && !isInitializing) {
      checkDemoMode();
    }
  }, [activeChatId, chatTabs, createNewChat, setDatasetForChat, isInitializing]);

  // ===== Message Handling =====

  const handleSendMessage = async (content: string, shouldPlayTTS: boolean = false, isVoiceInput: boolean = false) => {
    if (!activeChatId && chatTabs.length === 0) {
      createNewChat();
    }

    // Check for dataset connection (allow demo mode)
    const currentChat = activeChatId ? chatTabs.find(t => t.id === activeChatId) : null;
    if (!isConnectionVerified && (!currentChat || currentChat.datasetStatus !== 'ready')) {
      try {
        const statusResp = await api.getDatasetStatus();
        if (statusResp.loaded) {
          setIsConnectionVerified(true);
        } else {
          toast.error("Data not loaded", { description: "Please wait for the data to load or refresh the page." });
          return;
        }
      } catch {
        toast.error("Connection error", { description: "Could not verify data connection." });
        return;
      }
    }

    const containsTamil = /[\u0B80-\u0BFF]/.test(content);
    setIsProcessingQuery(true);
    setIsCurrentInputVoice(isVoiceInput);
    setHasTamilInput(containsTamil);

    const queryStartTime = Date.now();
    addMessage(content, 'user');

    try {
      const response = await api.sendMessage(content, sessionName);
      const latencyMs = Date.now() - queryStartTime;

      if (response.success) {
        const explanationText = response.explanation || "Here's what I found.";

        if (response.name_changed && response.new_name) {
          setSessionName(response.new_name);
        }

        addMessage(explanationText, 'assistant', {
          plan: response.plan,
          data: response.data,
          schema_context: response.schema_context,
          data_refreshed: response.data_refreshed,
          visualization: response.visualization
        }, undefined, latencyMs);

        if (isVoiceInput) {
          setLiveCaption({ text: explanationText, type: 'assistant' });
        }

        if (response.visualization) {
          setLastVisualization(response.visualization);
        }

        if (response.plan) {
          setExpandedVoiceSection('plan');
        }

        setFollowUpSuggestions(getRandomSuggestions());

        if (shouldPlayTTS) {
          await voice.playTextToSpeech(explanationText);
        } else {
          setIsProcessingQuery(false);
          setIsCurrentInputVoice(false);
          setHasTamilInput(false);
          setTimeout(() => setLiveCaption(null), 5000);
        }

      } else {
        const errorMsg = response.explanation || response.error || "Sorry, I encountered an error extracting that information.";
        toast.error("Query failed", { description: errorMsg });
        addMessage(errorMsg, 'assistant');
      }

    } catch (error: unknown) {
      console.error('Send message error:', error);
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
      setIsProcessingQuery(false);
      setIsCurrentInputVoice(false);
      setHasTamilInput(false);
    }
  };

  // Wire up the sendMessage ref for the voice hook
  sendMessageRef.current = handleSendMessage;

  // ===== Render =====

  return (
    <div className="flex h-[100dvh] w-full overflow-hidden bg-background text-foreground">
      {/* Data Loading Overlay (Phase 2: SSE progress) */}
      {showLoadingOverlay && (
        <DataLoadingOverlay
          status={loadingStatus}
          onRetry={() => {
            api.resetToDefault?.().then(() => {
              setShowLoadingOverlay(true);
            });
          }}
          onDismiss={() => setShowLoadingOverlay(false)}
        />
      )}

      {/* Sidebar */}
      <ChatSidebar
        isOpen={showChatsPanel}
        onClose={() => setShowChatsPanel(false)}
        chatTabs={chatTabs}
        activeChatId={activeChatId}
        onSwitchChat={switchChat}
        onDeleteChat={deleteChat}
        onRenameChat={renameChat}
        onNewChat={createNewChat}
        onOpenChat={() => setShowChat(true)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col relative min-w-0">
        {/* Background */}
        <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
          <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] bg-violet-500/8 rounded-full blur-[150px]" />
          <div className="absolute bottom-[-20%] right-[-10%] w-[600px] h-[600px] bg-purple-500/5 rounded-full blur-[150px]" />
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-background/50 to-background" />
        </div>

        {/* Header */}
        {voice.isFullscreenVoice && !showChat ? (
          <div className="absolute top-4 right-4 z-30">
            <Button
              variant="destructive"
              size="sm"
              onClick={voice.abruptEndVoiceMode}
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
              <DatasetInfoPopover
                datasetInfo={demoDatasetInfo || activeChat?.datasetStats || null}
                isConnected={isConnectionVerified}
                onClick={() => setIsDataSourcesPanelOpen(true)}
                onSuggestionClick={(text) => {
                  setShowChat(true);
                  setInputMessage(text);
                }}
              />

              <Button
                variant="ghost"
                onClick={() => {
                  const newShowChat = !showChat;
                  setShowChat(newShowChat);
                  if (newShowChat) {
                    // Exit fullscreen voice when switching to chat
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

              {/* Clear Chat Button */}
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
                className="relative z-10 w-full h-full flex items-center justify-center overflow-hidden"
              >
                {/* 3-Column Layout: Captions | Voice | Visualization */}
                <div className="w-full h-full grid grid-cols-1 lg:grid-cols-[1fr_auto_1fr] items-center gap-4 px-4 sm:px-6 lg:px-8">

                  {/* LEFT: Live Captions Panel */}
                  <LiveCaptions
                    caption={liveCaption}
                    isRecording={voice.isRecording}
                    isProcessing={voice.isProcessingVoice || isProcessingQuery}
                    isSpeaking={voice.isSpeaking}
                  />

                  {/* CENTER: Main Voice Interface */}
                  <div className="flex flex-col items-center justify-center gap-4 sm:gap-6 py-4 sm:py-8 max-w-md mx-auto">
                    {/* Brand Header */}
                    <motion.div
                      initial={{ opacity: 0, y: -20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2 }}
                      className="text-center space-y-2"
                    >
                      <h1 className="text-2xl sm:text-3xl md:text-4xl font-display font-bold tracking-tight">
                        {voice.isRecording ? (
                          <span className="text-violet-400">Listening<span className="animate-pulse">...</span></span>
                        ) : (voice.isProcessingVoice || isProcessingQuery) ? (
                          <span className="text-cyan-400">Processing<span className="animate-pulse">...</span></span>
                        ) : voice.isSpeaking ? (
                          <span className="text-purple-400">Speaking<span className="animate-pulse">...</span></span>
                        ) : (
                          <>Hello <span className="gradient-text">{sessionName}</span></>
                        )}
                      </h1>
                      <p className="text-zinc-500 text-xs sm:text-sm font-medium max-w-md mx-auto px-4">
                        {voice.isRecording
                          ? "Voice captured securely"
                          : (voice.isProcessingVoice || isProcessingQuery)
                            ? "Working on your request..."
                            : voice.isSpeaking
                              ? "Tap to stop"
                              : "Tap to start voice conversation"}
                      </p>
                    </motion.div>

                    {/* Voice Visualizer */}
                    <VoiceVisualizer
                      isRecording={voice.isRecording}
                      isSpeaking={voice.isSpeaking || voice.isProcessingVoice || isProcessingQuery}
                    />

                    {/* Voice Button */}
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      animate={voice.isRecording ? {
                        scale: [1, 1.05, 1],
                      } : {}}
                      transition={voice.isRecording ? {
                        duration: 1.5,
                        repeat: Infinity,
                        ease: "easeInOut"
                      } : {}}
                      onClick={() => {
                        if (voice.isSpeaking) {
                          voice.stopTextToSpeech();
                          return;
                        }
                        voice.handleVoiceToggle();
                      }}
                      aria-label={voice.isRecording ? "Tap to stop recording" : voice.isSpeaking ? "Stop speaking" : "Tap to start recording"}
                      className={`relative w-14 h-14 sm:w-16 sm:h-16 rounded-full transition-all duration-500 flex items-center justify-center ${voice.isRecording
                        ? 'bg-violet-500 shadow-[0_0_60px_rgba(139,92,246,0.5)]'
                        : voice.isSpeaking
                          ? 'bg-red-500 shadow-[0_0_60px_rgba(239,68,68,0.5)]'
                          : (voice.isProcessingVoice || isProcessingQuery)
                            ? 'bg-cyan-500/20 border-2 border-cyan-500 shadow-[0_0_40px_rgba(6,182,212,0.3)]'
                            : 'bg-secondary border border-border hover:border-primary/50 hover:shadow-[0_0_40px_rgba(var(--primary),0.2)]'
                        }`}
                    >
                      {voice.isRecording && (
                        <motion.span
                          className="absolute inset-0 rounded-full bg-violet-500"
                          animate={{ scale: [1, 1.5], opacity: [0.4, 0] }}
                          transition={{ duration: 1.2, repeat: Infinity, ease: "easeOut" }}
                        />
                      )}
                      {voice.isSpeaking && (
                        <motion.span
                          className="absolute inset-0 rounded-full bg-red-500"
                          animate={{ scale: [1, 1.5], opacity: [0.4, 0] }}
                          transition={{ duration: 1.2, repeat: Infinity, ease: "easeOut" }}
                        />
                      )}
                      {(voice.isProcessingVoice || isProcessingQuery) && !voice.isRecording && !voice.isSpeaking && (
                        <motion.span
                          className="absolute inset-0 rounded-full border-2 border-cyan-500"
                          animate={{ scale: [1, 1.3], opacity: [0.6, 0] }}
                          transition={{ duration: 1.5, repeat: Infinity, ease: "easeOut" }}
                        />
                      )}
                      <AnimatePresence mode="wait">
                        {voice.isSpeaking ? (
                          <motion.div key="stop-speaking" initial={{ scale: 0, rotate: -90 }} animate={{ scale: 1, rotate: 0 }} exit={{ scale: 0, rotate: 90 }}>
                            <StopCircle className="w-6 h-6 text-white" />
                          </motion.div>
                        ) : voice.isRecording ? (
                          <motion.div key="stop" initial={{ scale: 0, rotate: -90 }} animate={{ scale: 1, rotate: 0 }} exit={{ scale: 0, rotate: 90 }}>
                            <Square className="w-6 h-6 text-white fill-current" />
                          </motion.div>
                        ) : voice.isProcessingVoice ? (
                          <motion.div key="loading" initial={{ scale: 0, rotate: 90 }} animate={{ scale: 1, rotate: 0 }} exit={{ scale: 0, rotate: -90 }}>
                            <Loader2 className="w-8 h-8 text-primary animate-spin" />
                          </motion.div>
                        ) : (
                          <motion.div key="mic" initial={{ scale: 0, rotate: 90 }} animate={{ scale: 1, rotate: 0 }} exit={{ scale: 0, rotate: -90 }}>
                            <Mic className="w-6 h-6 text-muted-foreground" />
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </motion.button>

                    {/* Voice Latency Badge */}
                    {voice.voiceLatencyMs !== null && (
                      <motion.div
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-zinc-800/60 border border-zinc-700/40"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        <span className="text-[10px] font-mono text-zinc-400 tabular-nums">
                          {voice.voiceLatencyMs >= 1000
                            ? `${(voice.voiceLatencyMs / 1000).toFixed(1)}s`
                            : `${voice.voiceLatencyMs}ms`}
                        </span>
                        <span className="text-[9px] text-zinc-600">latency</span>
                      </motion.div>
                    )}

                    {/* Mobile Caption Display */}
                    <MobileCaptions
                      caption={liveCaption}
                      isRecording={voice.isRecording}
                      isProcessing={voice.isProcessingVoice || isProcessingQuery}
                      isSpeaking={voice.isSpeaking}
                      onOpenChat={() => setShowChat(true)}
                    />

                    {/* Animated Suggestion Pill */}
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2 }}
                      className="w-full max-w-xl mx-auto px-4"
                    >
                      <VoiceModeInput
                        suggestions={[
                          "Which month recorded the highest total profit?",
                          "Are sales increasing or decreasing in Chennai?",
                          "Which category shows consistent growth?",
                          "How many transactions were made using UPI?"
                        ]}
                        onSend={(text) => {
                          setShowChat(true);
                          setTimeout(() => {
                            handleSendMessage(text, false, false);
                          }, 100);
                        }}
                        onOpenChat={() => setShowChat(true)}
                      />
                    </motion.div>
                  </div>

                  {/* RIGHT: Visualization Panel - REMOVED */}
                </div>
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
                              {(smartSuggestions.length > 0 ? smartSuggestions.slice(0, 3) : ["What is the total for last month?", "Show me the top 5 categories", "Compare trends over time"]).map((suggestion) => (
                                <button
                                  key={suggestion}
                                  onClick={() => setInputMessage(suggestion)}
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
                            message={{ ...msg, isSpeaking: voice.speakingMessageId === msg.id }}
                            onPlay={voice.playTextToSpeech}
                            onStop={voice.stopTextToSpeech}
                          />
                        ))}
                        {/* Follow-up suggestions */}
                        {messages.length > 0 && messages[messages.length - 1].role === 'assistant' && !isProcessingQuery && !voice.isProcessingVoice && (
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
                                  onClick={() => setInputMessage(suggestion)}
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
                    {/* Processing status */}
                    <AnimatePresence>
                      {(voice.isProcessingVoice || isProcessingQuery) && (
                        <ProcessingStatus
                          isProcessing={true}
                          isVoiceInput={isCurrentInputVoice}
                          hasTamilInput={hasTamilInput}
                          variant="chat"
                        />
                      )}
                    </AnimatePresence>
                    {voice.isSpeaking && (
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
                    <div className="flex items-center gap-1.5 sm:gap-2 p-1.5 sm:p-2 rounded-xl sm:rounded-2xl glass border border-border bg-card/80 backdrop-blur-xl h-[48px] sm:h-[56px] overflow-hidden">
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
                      {/* Mic Button */}
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        animate={voice.isRecording ? {
                          scale: [1, 1.1, 1],
                          boxShadow: [
                            '0 0 0 0 rgba(139, 92, 246, 0.4)',
                            '0 0 0 10px rgba(139, 92, 246, 0)',
                            '0 0 0 0 rgba(139, 92, 246, 0)'
                          ]
                        } : {}}
                        transition={voice.isRecording ? {
                          duration: 1.2,
                          repeat: Infinity,
                          ease: "easeInOut"
                        } : {}}
                        onClick={() => {
                          if (!voice.isVoiceEnabledInChat) {
                            voice.setIsVoiceEnabledInChat(true);
                          }
                          voice.handleVoiceToggle();
                        }}
                        aria-label={voice.isRecording ? "Stop recording" : "Start recording"}
                        className={cn(
                          "w-9 h-9 sm:w-10 sm:h-10 rounded-lg sm:rounded-xl transition-all duration-300 flex items-center justify-center flex-shrink-0 relative",
                          voice.isRecording
                            ? 'bg-violet-500 shadow-[0_0_30px_rgba(139,92,246,0.6)]'
                            : 'bg-secondary border border-border hover:border-primary/50'
                        )}
                      >
                        {voice.isRecording && (
                          <motion.span
                            className="absolute inset-0 rounded-lg sm:rounded-xl bg-violet-500"
                            animate={{ scale: [1, 1.4], opacity: [0.5, 0] }}
                            transition={{ duration: 1, repeat: Infinity, ease: "easeOut" }}
                          />
                        )}
                        <AnimatePresence mode="wait">
                          {voice.isRecording ? (
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
                      {/* Send Button */}
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

      {/* Data Sources Panel */}
      <DataSourcesPanel
        isOpen={isDataSourcesPanelOpen}
        onClose={() => setIsDataSourcesPanelOpen(false)}
        onAddSource={() => {
          toast.info("Add more data sources", {
            description: "Use the backend /api/load-source endpoint to add CSV, Excel, or Drive files."
          });
        }}
        onRefresh={() => {
          api.getDatasetStatus().then((status) => {
            if (status.loaded) {
              setIsConnectionVerified(true);
              setDemoDatasetInfo({
                totalTables: status.total_tables || 0,
                totalRecords: status.total_records || 0,
                sheetCount: status.original_sheets?.length || 0,
                sheets: status.original_sheets || [],
                detectedTables: status.detected_tables || [],
                tableProfiles: status.table_profiles_summary || [],
                sourceType: status.source_type || 'unknown',
                smartSuggestions: status.smart_suggestions || [],
              });
              if (status.smart_suggestions?.length) {
                setSmartSuggestions(status.smart_suggestions);
              }
              toast.success("Data refreshed");
            }
          });
        }}
      />
    </div>
  );
}
