'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppState } from '@/lib/hooks';
import { MessageBubble } from './MessageBubble';
import { Button } from '@/components/ui/button';
import { VoiceVisualizer } from './VoiceVisualizer';
import { apiClient } from '@/lib/api-client';
import { audioRecorder } from '@/lib/audio-recorder';
import { audioPlayer } from '@/lib/audio-player';
import { useAudioState } from '@/lib/audio-state';
// INJECTED: Loading Panel
import { DatasetLoadingPanel } from './DatasetLoadingPanel';

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
  Moon,
  Sun,
  Monitor
} from 'lucide-react';
import { toast } from 'sonner';
import { useTheme } from 'next-themes';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog";
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

interface ChatScreenProps {
  onLogout: () => void;
  username: string;
}

export function ChatScreen({ onLogout, username }: ChatScreenProps) {
  const {
    messages,
    addMessage,
    config,
    setGoogleSheetUrl,
    chatTabs,
    activeChatId,
    createNewChat,
    switchChat,
    deleteChat,
    clearChat,
    updateChatSheet,
    // INJECTED: Dataset State
    datasetState,
    currentLoadingStage,
    loadingStageMessage,
    isInitializing,
    sheetUrl,
    setSheetUrl
  } = useAppState();

  const [isRecording, setIsRecording] = useState(false);
  const [currentLanguage, setCurrentLanguage] = useState<string>('en');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showChat, setShowChat] = useState(false);
  const [showChatsPanel, setShowChatsPanel] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [isSheetConnected, setIsSheetConnected] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { theme, setTheme } = useTheme();

  // Use shared audio state
  const { isPlaying: isSpeaking, setIsPlaying: setIsSpeaking } = useAudioState();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, showChat]);

  // Track sheet connection per chat session - PERSISTED TO LOCALSTORAGE
  const [chatSheetMap, setChatSheetMap] = useState<Record<string, boolean>>(() => {
    // Load from localStorage on mount
    const saved = localStorage.getItem('chatSheetMap');
    return saved ? JSON.parse(saved) : {};
  });
  const [isLoadingSheet, setIsLoadingSheet] = useState(false);
  const [loadingStep, setLoadingStep] = useState<string>('');
  const [loadingProgress, setLoadingProgress] = useState<number>(0);

  // Dataset details state
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [datasetDetails, setDatasetDetails] = useState<any>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);


  // Persist chatSheetMap to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('chatSheetMap', JSON.stringify(chatSheetMap));
  }, [chatSheetMap]);

  // CRITICAL: Verify backend state on mount - don't trust localStorage alone!
  // This ensures frontend state matches actual backend state
  useEffect(() => {
    const verifyBackendState = async () => {
      try {
        // Check if backend actually has a sheet loaded
        const status = await apiClient.getSheetStatus();

        if (status.is_loaded && status.sheet_url) {
          // Backend has sheet loaded - sync frontend state
          console.log('✓ Backend has sheet loaded:', status.sheet_url);

          // Update config if needed
          if (config.googleSheetUrl !== status.sheet_url) {
            setGoogleSheetUrl(status.sheet_url);
          }

          // Mark current chat as having sheet loaded AND set connected state
          if (activeChatId && !chatSheetMap[activeChatId]) {
            setChatSheetMap(prev => ({
              ...prev,
              [activeChatId]: true
            }));
          }

          // CRITICAL: Mark as connected so we don't reconnect unnecessarily
          setIsSheetConnected(true);
        } else {
          // Backend doesn't have sheet loaded - clear frontend state
          console.log('✓ Backend has no sheet loaded - ready for new connection');
          setChatSheetMap({});
          localStorage.removeItem('chatSheetMap');
          setIsSheetConnected(false);
        }
      } catch (error) {
        console.error('❌ Failed to verify backend state:', error);
        // Only show error if it's a real connection failure (not just "no sheet loaded")
        if (error instanceof TypeError && error.message.includes('fetch')) {
          toast.error("Backend Connection Failed", {
            description: "Could not connect to API server. Please ensure the backend is running.",
          });
        }
        // On error, assume not loaded to be safe
        setChatSheetMap({});
        localStorage.removeItem('chatSheetMap');
        setIsSheetConnected(false);
      }
    };

    verifyBackendState();
  }, []); // Run once on mount

  // MANDATORY: Force sheet connection dialog for new chats, but AUTO-CONNECT for existing ones
  // This is the entry gate - no bypass allowed
  useEffect(() => {
    if (isInitializing) return; // Wait for state to load!

    if (activeChatId) {
      if (!sheetUrl) {
        // No sheet associated with this chat yet -> FORCE MODAL
        console.log('📋 New chat detected - showing sheet connection modal');
        setIsModalOpen(true);
        setIsSheetConnected(false);
      } else {
        // Sheet URL exists for this chat
        // Check if backend already has it loaded (from verifyBackendState)
        if (chatSheetMap[activeChatId]) {
          // Backend already has this sheet loaded - mark as connected
          console.log('✅ Sheet already loaded in backend for this chat');
          setIsSheetConnected(true);
          setIsModalOpen(false);
        } else if (!isSheetConnected && !isLoadingSheet) {
          // Sheet URL exists but backend doesn't have it -> SILENT RECONNECT
          console.log('🔄 Auto-connecting to persisted sheet:', sheetUrl);
          handleSaveSheet();
        }
      }
    }
  }, [activeChatId, sheetUrl, isSheetConnected, isLoadingSheet, isInitializing, chatSheetMap]);


  const handleSendMessage = async (content: string, language?: string) => {
    if (!activeChatId) {
      createNewChat();
    }
    addMessage(content, 'user');

    try {
      setIsSpeaking(true);

      // Call real API
      const response = await apiClient.sendMessage(content, activeChatId || undefined);

      // Add assistant response
      addMessage(response.message, 'assistant');

      // Play TTS audio for response (multilingual)
      try {
        await audioPlayer.playText(response.message, language);
      } catch (ttsError) {
        console.error('TTS error:', ttsError);
        // Continue even if TTS fails
      }

      setIsSpeaking(false);

      // Show success toast if query was successful
      if (response.metadata?.success) {
        toast.success("Query processed", {
          description: `Found ${response.metadata.result_count || 0} results`,
        });
      }
    } catch (error) {
      setIsSpeaking(false);
      const errorMessage = error instanceof Error ? error.message : 'Failed to process query';
      addMessage(`Error: ${errorMessage}`, 'assistant');
      toast.error("Query failed", {
        description: errorMessage,
      });
    }
  };

  const handleVoiceToggle = async () => {
    // Block if sheet not connected
    if (!isSheetConnected) {
      toast.error("Sheet Required", {
        description: "Please connect a Google Sheet first",
      });
      setIsModalOpen(true);
      return;
    }

    if (isRecording) {
      // Stop recording and transcribe
      try {
        setIsRecording(false);

        toast.info("Processing...", {
          description: "Transcribing your voice...",
        });

        // Stop recording and get audio blob
        const audioBlob = await audioRecorder.stopRecording();

        // Send to ElevenLabs for transcription
        const result = await apiClient.transcribeAudio(audioBlob);

        // Show transcribed text immediately
        toast.success("Transcribed!", {
          description: `"${result.text.substring(0, 50)}..."`,
        });

        // Add user message to chat immediately
        addMessage(result.text, 'user');

        // Send the transcribed text and get AI response
        setCurrentLanguage(result.language);
        setIsSpeaking(true);

        try {
          const response = await apiClient.sendMessage(result.text, activeChatId || undefined);

          // Add assistant response
          addMessage(response.message, 'assistant');

          // Play TTS audio for response in the SAME language as input
          try {
            console.log('Playing TTS in language:', result.language);
            console.log('Response text:', response.message);

            await audioPlayer.playText(response.message, result.language);
            // Only turn off speaking after audio finishes
            setIsSpeaking(false);

            toast.success("Response complete!", {
              description: `Voice playback finished (${result.language})`,
            });
          } catch (ttsError) {
            console.error('TTS error:', ttsError);
            setIsSpeaking(false);
          }
        } catch (error) {
          setIsSpeaking(false);
          const errorMessage = error instanceof Error ? error.message : 'Failed to process query';
          addMessage(`Error: ${errorMessage}`, 'assistant');
          toast.error("Query failed", {
            description: errorMessage,
          });
        }
      } catch (error) {
        console.error('Transcription error:', error);
        const errorMsg = error instanceof Error ? error.message : 'Failed to transcribe audio';

        // Handle API Key errors specifically
        if (errorMsg.includes('401') || errorMsg.includes('403') || errorMsg.includes('unusual activity')) {
          toast.error("Voice Service Unavailable", {
            description: "Your ElevenLabs API key may be invalid or exhausted. Please check backend/.env",
            duration: 5000,
          });
        } else {
          toast.error("Transcription failed", {
            description: errorMsg,
          });
        }
      }
    } else {
      // Start recording
      try {
        setIsRecording(true);
        setIsSpeaking(false);

        // Stop any playing audio
        audioPlayer.stop();

        // Start recording
        await audioRecorder.startRecording();

        toast.info("Recording...", {
          description: "Speak now. Click again to stop.",
        });
      } catch (error) {
        console.error('Recording error:', error);
        setIsRecording(false);
        toast.error("Microphone error", {
          description: error instanceof Error ? error.message : 'Could not access microphone',
        });
      }
    }
  };

  const handleSaveSheet = async () => {
    // Validate URL format
    if (!sheetUrl.trim()) {
      toast.error("Invalid URL", {
        description: "Please enter a valid Google Sheets URL",
      });
      return;
    }

    // Check URL structure
    if (!sheetUrl.includes('docs.google.com/spreadsheets')) {
      toast.error("Invalid URL Format", {
        description: "Please enter a valid Google Sheets URL",
      });
      return;
    }

    setIsLoadingSheet(true);
    // Note: Progress is now handled by DatasetLoadingPanel takeover, 
    // but we keep this here for logic consistency if panel doesn't trigger immediately
    setLoadingProgress(0);
    setLoadingStep('Starting connection...');

    try {
      console.log('[Sheet Loading] Starting connection to:', sheetUrl);

      // Call API with progress callback
      // NOTE: Our modified apiClient now maps SSE stages to this callback
      const response = await apiClient.connectSheet(sheetUrl, (progressData) => {
        console.log('[Sheet Loading] Progress:', progressData);
        setLoadingStep(progressData.message);

        // Map common stages to progress numbers for legacy UI parts
        const stage = progressData.stage.toLowerCase();
        let progress = 10;
        if (stage.includes('fetch')) progress = 30;
        if (stage.includes('detect')) progress = 50;
        if (stage.includes('load')) progress = 70;
        if (stage.includes('schema')) progress = 85;
        if (stage.includes('embed')) progress = 90;
        if (stage.includes('ready')) progress = 100;

        setLoadingProgress(progress);
      });

      console.log('[Sheet Loading] API response:', response);

      if (response.success) {
        // Sheet successfully loaded
        const sheetName = response.sheet_name || 'Google Sheet';

        // Show final progress
        setLoadingProgress(100);
        setLoadingStep('✅ Complete!');

        setGoogleSheetUrl(sheetUrl);
        setIsSheetConnected(true);

        // CRITICAL: Mark this chat as having a sheet connected
        if (activeChatId && updateChatSheet) {
          setChatSheetMap(prev => ({
            ...prev,
            [activeChatId]: true
          }));

          // Store sheet info in the chat tab (using our injected hook function)
          updateChatSheet(activeChatId, sheetUrl, sheetName);
        }

        await new Promise(resolve => setTimeout(resolve, 500));
        setIsLoadingSheet(false);
        setLoadingProgress(0);
        setLoadingStep('');
        setIsModalOpen(false);

        toast.success("Dataset Loaded Successfully!", {
          description: `Connected to "${sheetName}"`,
        });

        // Stay on Voice Home screen (do not force chat view)

      } else {
        // Validation or loading failed
        setIsLoadingSheet(false);
        setLoadingProgress(0);
        setLoadingStep('');
        toast.error("Failed to Load Dataset", {
          description: response.message || "Please check the URL and try again",
        });
      }
    } catch (error) {
      console.error('[Sheet Loading] Error:', error);
      setIsLoadingSheet(false);
      setLoadingProgress(0);
      setLoadingStep('');
      const errorMessage = error instanceof Error ? error.message : 'Failed to connect sheet';
      toast.error("Connection Error", {
        description: errorMessage,
      });
    }
  };

  const handleViewDetails = async () => {
    setLoadingDetails(true);
    try {
      const details = await apiClient.getSheetDetails();
      if (details.success) {
        setDatasetDetails(details);
        setShowDetailsModal(true);
      } else {
        toast.error("No Data Available", {
          description: details.message || "Please load a dataset first",
        });
      }
    } catch (error) {
      console.error('[Dataset Details] Error:', error);
      toast.error("Failed to Load Details", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleNewChat = () => {
    createNewChat();
    setShowChatsPanel(false);
    toast.success("New conversation started");
  };

  // ===================================
  // INJECTED: Dataset Loading Panel
  // ===================================
  // This takes over the UI when useAppState detects a loading state
  if (datasetState === 'LOADING' && currentLoadingStage) {
    return (
      <DatasetLoadingPanel
        sheetUrl={sheetUrl}
        currentStage={currentLoadingStage}
        stageMessage={loadingStageMessage}
      />
    );
  }

  // ===================================
  // Original Cinematic UI
  // ===================================
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      {/* Your Chats Sidebar */}
      <AnimatePresence>
        {showChatsPanel && (
          <motion.div
            initial={{ x: -320, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -320, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="absolute left-0 top-0 bottom-0 w-80 z-50 glass border-r border-zinc-800/50 flex flex-col"
          >
            <div className="p-6 border-b border-zinc-800/50">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold font-display tracking-tight">Your Chats</h3>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowChatsPanel(false)}
                  className="h-9 w-9 rounded-xl hover:bg-zinc-800"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>

            <div className="p-4">
              <Button
                onClick={handleNewChat}
                className="w-full h-12 bg-green-600 hover:bg-green-500 text-white rounded-xl font-semibold gap-2 transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                <Plus className="w-4 h-4" />
                New Chat
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto px-3 pb-4 hide-scrollbar">
              {chatTabs.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 opacity-40">
                  <MessageCircle className="w-10 h-10 mb-3" />
                  <p className="text-sm font-medium">No conversations yet</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {chatTabs.map((tab) => (
                    <motion.div
                      key={tab.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`group relative p-4 rounded-xl cursor-pointer transition-all ${activeChatId === tab.id
                        ? 'bg-green-500/10 border border-green-500/20'
                        : 'hover:bg-zinc-800/50 border border-transparent'
                        }`}
                      onClick={() => {
                        switchChat(tab.id);
                        setShowChatsPanel(false);
                        setShowChat(true);
                      }}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold text-sm truncate">{tab.title}</p>
                          <p className="text-xs text-zinc-500 mt-1">
                            {tab.messages.length} messages
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteChat(tab.id);
                          }}
                          className="h-8 w-8 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-500/20 hover:text-red-400 transition-all"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Chats Panel Overlay */}
      <AnimatePresence>
        {showChatsPanel && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowChatsPanel(false)}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm z-40"
          />
        )}
      </AnimatePresence>

      {/* Main Content */}
      <div className="flex-1 flex flex-col relative">
        {/* Background */}
        <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
          <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] bg-green-500/8 dark:bg-green-500/8 rounded-full blur-[150px]" />
          <div className="absolute bottom-[-20%] right-[-10%] w-[600px] h-[600px] bg-teal-500/5 dark:bg-teal-500/5 rounded-full blur-[150px]" />
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-background/50 to-background" />
        </div>

        {/* Header */}
        <header className="relative z-20 flex items-center justify-between px-6 py-5">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              onClick={() => setShowChatsPanel(true)}
              className="h-11 px-4 rounded-xl glass border border-border hover:border-green-500/30 hover:bg-accent transition-all gap-3"
            >
              <MessageSquarePlus className="w-4 h-4 text-green-400" />
              <span className="text-sm font-medium">Your Chats</span>
              {chatTabs.length > 0 && (
                <span className="ml-1 px-2 py-0.5 text-xs font-bold bg-green-500/20 text-green-400 rounded-full">
                  {chatTabs.length}
                </span>
              )}
            </Button>

            {showChat && (
              <Button
                variant="ghost"
                onClick={() => {
                  if (confirm('Are you sure you want to clear this chat?')) {
                    clearChat();
                    toast.success("Chat cleared");
                  }
                }}
                className="h-11 px-4 rounded-xl glass border border-border hover:border-red-500/30 hover:bg-red-500/10 hover:text-red-400 transition-all gap-2"
                title="Clear Chat"
              >
                <Trash2 className="w-4 h-4" />
                <span className="text-sm font-medium hidden md:inline">Clear</span>
              </Button>
            )}
          </div>

          <div className="flex items-center gap-3">
            <Dialog
              open={isModalOpen}
              onOpenChange={(open) => {
                // STRICT: Prevent closing dialog if sheet not connected
                if (!open && !isSheetConnected) {
                  toast.warning("Dataset Required", {
                    description: "Please connect a Google Sheet to continue",
                  });
                  return; // Don't allow closing
                }
                setIsModalOpen(open);
              }}
            >
              <DialogTrigger asChild>
                <Button
                  variant="ghost"
                  className="h-11 px-4 rounded-xl glass border border-border hover:border-green-500/30 hover:bg-accent transition-all gap-2"
                >
                  <Table className="w-4 h-4 text-zinc-400" />
                  <span className="text-sm font-medium">
                    {isSheetConnected ? '✓ Dataset Loaded' : 'Connect Dataset'}
                  </span>
                </Button>
              </DialogTrigger>
              <DialogContent
                className="bg-card border-border text-card-foreground sm:max-w-md"
                onInteractOutside={(e) => {
                  // STRICT: Prevent closing on outside click if not connected
                  if (!isSheetConnected) {
                    e.preventDefault();
                    toast.warning("Dataset Required", {
                      description: "Please connect a Google Sheet to continue",
                    });
                  }
                }}
                onEscapeKeyDown={(e) => {
                  // STRICT: Prevent closing on Escape if not connected
                  if (!isSheetConnected) {
                    e.preventDefault();
                  }
                }}
              >
                <DialogHeader>
                  <DialogTitle className="text-xl font-display font-bold">
                    {isSheetConnected ? 'Dataset Status' : 'Connect Your Dataset'}
                  </DialogTitle>
                  <DialogDescription className="text-sm text-muted-foreground mt-2">
                    {isSheetConnected
                      ? 'View your connected dataset or connect a new one for a new chat.'
                      : 'Required: Paste your Google Sheets URL to begin'
                    }
                  </DialogDescription>
                </DialogHeader>
                {!isSheetConnected && (
                  <p className="sr-only">Required: Paste your Google Sheets URL to begin</p>
                )}
                {isSheetConnected && activeChatId && (
                  <p className="text-sm text-green-400 mt-2 px-6">
                    ✓ Connected to: {chatTabs.find(t => t.id === activeChatId)?.sheetName || 'Google Sheet'}
                  </p>
                )}
                <div className="space-y-4 py-4 px-6 md:px-0">
                  <div className="space-y-2">
                    <label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Sheet URL</label>
                    <Input
                      value={sheetUrl}
                      onChange={(e) => setSheetUrl(e.target.value)}
                      placeholder="https://docs.google.com/spreadsheets/d/..."
                      className="bg-background border-border focus:border-green-500/50 h-12 rounded-xl"
                      disabled={isSheetConnected || isLoadingSheet}
                      readOnly={isSheetConnected}
                    />
                  </div>

                  {/* Loading Progress UI */}
                  {isLoadingSheet && (
                    <div className="space-y-3 p-4 rounded-xl bg-green-500/5 border border-green-500/20">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-green-400">{loadingStep}</span>
                        <span className="text-xs font-bold text-green-400">{loadingProgress}%</span>
                      </div>
                      <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-green-500 to-teal-400 transition-all duration-500 ease-out"
                          style={{ width: `${loadingProgress}%` }}
                        />
                      </div>
                      <div className="flex items-center gap-2 text-xs text-zinc-400">
                        <div className="flex gap-1">
                          {[0, 1, 2].map((i) => (
                            <div
                              key={i}
                              className="w-1 h-3 bg-green-400 rounded-full animate-pulse"
                              style={{ animationDelay: `${i * 0.15}s` }}
                            />
                          ))}
                        </div>
                        <span>Please wait...</span>
                      </div>
                    </div>
                  )}

                  {!isSheetConnected && (
                    <Button
                      onClick={handleSaveSheet}
                      disabled={isLoadingSheet}
                      className="w-full bg-green-600 hover:bg-green-500 text-white font-bold rounded-xl h-12 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                    >
                      {isLoadingSheet ? 'Connecting...' : 'Connect to Kiwi'}
                    </Button>
                  )}
                  {isSheetConnected && (
                    <>
                      <Button
                        onClick={handleViewDetails}
                        disabled={loadingDetails}
                        className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl h-11 transition-all hover:scale-[1.02] active:scale-[0.98]"
                      >
                        {loadingDetails ? 'Loading...' : '📊 View Details'}
                      </Button>
                      <div className="text-center text-sm text-muted-foreground">
                        Dataset is locked for this chat session
                      </div>
                    </>
                  )}
                </div>
              </DialogContent>
            </Dialog>

            {/* Dataset Details Modal - Premium Redesign */}
            {showDetailsModal && datasetDetails && (
              <Dialog open={showDetailsModal} onOpenChange={setShowDetailsModal}>
                <DialogContent className="max-w-4xl h-[85vh] flex flex-col p-0 gap-0 bg-card border-border overflow-hidden rounded-2xl">
                  <DialogHeader className="p-6 pb-4 border-b border-border bg-background/50 backdrop-blur-xl z-20">
                    <DialogTitle className="text-2xl font-display font-bold flex items-center gap-2">
                      <Table className="w-6 h-6 text-green-500" />
                      Dataset Overview
                    </DialogTitle>
                    <DialogDescription className="text-sm text-muted-foreground">
                      Connected to <span className="font-semibold text-foreground">{datasetDetails.spreadsheet_name || 'Google Sheet'}</span>
                    </DialogDescription>
                  </DialogHeader>

                  <div className="flex-1 overflow-y-auto overflow-x-hidden p-6 space-y-8 custom-scrollbar">
                    {/* Summary Stats Cards */}
                    <div className="grid grid-cols-3 gap-5">
                      <div className="p-5 rounded-2xl bg-gradient-to-br from-blue-500/10 to-blue-600/5 border border-blue-500/20 shadow-sm">
                        <div className="flex items-center gap-3 mb-2">
                          <div className="p-2 rounded-lg bg-blue-500/20 text-blue-400">
                            <Table className="w-5 h-5" />
                          </div>
                          <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Tables</span>
                        </div>
                        <p className="text-3xl font-bold text-foreground">{datasetDetails.total_tables}</p>
                      </div>

                      <div className="p-5 rounded-2xl bg-gradient-to-br from-green-500/10 to-emerald-600/5 border border-green-500/20 shadow-sm">
                        <div className="flex items-center gap-3 mb-2">
                          <div className="p-2 rounded-lg bg-green-500/20 text-green-400">
                            <MessageCircle className="w-5 h-5" />
                          </div>
                          <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Total Rows</span>
                        </div>
                        <p className="text-3xl font-bold text-foreground">{datasetDetails.total_rows.toLocaleString()}</p>
                      </div>

                      <div className="p-5 rounded-2xl bg-gradient-to-br from-purple-500/10 to-violet-600/5 border border-purple-500/20 shadow-sm">
                        <div className="flex items-center gap-3 mb-2">
                          <div className="p-2 rounded-lg bg-purple-500/20 text-purple-400">
                            <User className="w-5 h-5" />
                          </div>
                          <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Sheets</span>
                        </div>
                        <p className="text-3xl font-bold text-foreground">{datasetDetails.sheet_count}</p>
                      </div>
                    </div>

                    {/* Detailed Breakdown */}
                    <div className="space-y-6">
                      <h3 className="text-lg font-bold flex items-center gap-2 pb-2 border-b border-border">
                        <span className="w-1 h-6 bg-green-500 rounded-full"></span>
                        Structure Breakdown
                      </h3>

                      <div className="grid gap-6">
                        {datasetDetails.sheets.map((sheet: any, idx: number) => (
                          <div key={idx} className="group border border-border rounded-xl bg-card/50 hover:bg-accent/30 transition-all duration-300 overflow-hidden shadow-sm hover:shadow-md hover:border-green-500/30">
                            {/* Sheet Header */}
                            <div className="p-4 bg-muted/30 border-b border-border/50 flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-lg bg-background border border-border flex items-center justify-center text-xl shadow-sm">
                                  📄
                                </div>
                                <div>
                                  <h4 className="font-bold text-base">{sheet.sheet_name}</h4>
                                  <p className="text-xs text-muted-foreground">{sheet.tables.length} Detected Table{sheet.tables.length !== 1 && 's'}</p>
                                </div>
                              </div>
                            </div>

                            {/* Tables List */}
                            <div className="p-2">
                              {sheet.tables.map((table: any, tIdx: number) => (
                                <div key={tIdx} className="mb-2 last:mb-0">
                                  <details className="group/table">
                                    <summary className="list-none p-3 rounded-lg hover:bg-background border border-transparent hover:border-border cursor-pointer transition-all">
                                      <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3 min-w-0">
                                          <div className="w-8 h-8 rounded-md bg-green-500/10 text-green-500 flex items-center justify-center">
                                            <Table className="w-4 h-4" />
                                          </div>
                                          <div className="min-w-0">
                                            <p className="font-semibold text-sm truncate pr-4">{table.table_name}</p>
                                            <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                                              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-green-500"></span> {table.row_count.toLocaleString()} rows</span>
                                              <span className="w-[1px] h-3 bg-border"></span>
                                              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span> {table.column_count} cols</span>
                                            </div>
                                          </div>
                                        </div>
                                        <ChevronRight className="w-4 h-4 text-muted-foreground transition-transform group-open/table:rotate-90" />
                                      </div>
                                    </summary>

                                    {/* Columns content */}
                                    <div className="pl-14 pr-4 pb-4 pt-1">
                                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                                        {table.columns.map((col: string, cIdx: number) => (
                                          <div key={cIdx} className="text-xs px-2.5 py-1.5 rounded-md bg-muted/50 border border-border/50 text-muted-foreground font-mono truncate hover:bg-muted hover:text-foreground transition-colors" title={col}>
                                            {col}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  </details>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="p-4 border-t border-border bg-background/50 backdrop-blur z-20 flex justify-end">
                    <Button onClick={() => setShowDetailsModal(false)} variant="outline" className="rounded-xl">
                      Close
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            )}

            <Button
              variant="ghost"
              onClick={() => setShowChat(!showChat)}
              className={`h-11 px-4 rounded-xl border transition-all gap-2 ${showChat
                ? 'bg-green-500 text-white border-green-400 hover:bg-green-400'
                : 'glass border-border hover:border-green-500/30 hover:bg-accent'
                }`}
            >
              <MessageCircle className="w-4 h-4" />
              <span className="text-sm font-medium">Chat</span>
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-11 w-11 rounded-xl glass border border-border hover:border-green-500/30 hover:bg-accent transition-all"
                >
                  <User className="w-4 h-4 text-zinc-400" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56 bg-card border-border text-card-foreground">
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium leading-none">{username}</p>
                    <p className="text-xs leading-none text-muted-foreground">Kiwi Assistant User</p>
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
                      ? 'border-green-500 bg-green-500/10'
                      : 'border-border hover:border-muted-foreground bg-muted'
                      }`}
                  >
                    <Sun className="w-5 h-5" />
                    <span className="text-xs font-medium">Light</span>
                  </button>
                  <button
                    onClick={() => setTheme('system')}
                    className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${theme === 'system'
                      ? 'border-green-500 bg-green-500/10'
                      : 'border-border hover:border-muted-foreground bg-muted'
                      }`}
                  >
                    <Monitor className="w-5 h-5" />
                    <span className="text-xs font-medium">System</span>
                  </button>
                  <button
                    onClick={() => setTheme('dark')}
                    className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${theme === 'dark'
                      ? 'border-green-500 bg-green-500/10'
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
                className="relative z-10 w-full max-w-2xl flex flex-col items-center gap-4 px-6 py-4"
              >
                {/* Brand Header */}
                <motion.div
                  initial={{ opacity: 0, y: -20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className="text-center space-y-2"
                >
                  <h1 className="text-4xl font-display font-bold tracking-tight">
                    {isRecording ? (
                      <span className="text-green-400">Listening<span className="animate-pulse">...</span></span>
                    ) : isSpeaking ? (
                      <span className="text-teal-400">Speaking<span className="animate-pulse">...</span></span>
                    ) : (
                      <>Hey, <span className="gradient-text">{username}</span></>
                    )}
                  </h1>
                  <p className="text-zinc-500 text-sm font-medium max-w-md mx-auto">
                    {isRecording
                      ? "Your voice is being captured securely"
                      : isSpeaking
                        ? "Generating intelligent response"
                        : "Tap the button below to start a voice conversation"}
                  </p>
                </motion.div>

                {/* Voice Visualizer */}
                <VoiceVisualizer isRecording={isRecording} isSpeaking={isSpeaking} />

                {/* Voice Button */}
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleVoiceToggle}
                  className={`relative w-16 h-16 rounded-full transition-all duration-500 flex items-center justify-center ${isRecording
                    ? 'bg-green-500 shadow-[0_0_60px_rgba(34,197,94,0.5)]'
                    : 'bg-secondary border border-border hover:border-primary/50 hover:shadow-[0_0_40px_rgba(var(--primary),0.2)]'
                    }`}
                >
                  <AnimatePresence mode="wait">
                    {isRecording ? (
                      <motion.div
                        key="stop"
                        initial={{ scale: 0, rotate: -90 }}
                        animate={{ scale: 1, rotate: 0 }}
                        exit={{ scale: 0, rotate: 90 }}
                      >
                        <Square className="w-6 h-6 text-white fill-current" />
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

                {/* Action Buttons */}
                <div className="flex items-center gap-2 mt-3">
                  <Button
                    variant="ghost"
                    onClick={() => toast.success("Query Plan")}
                    className="h-9 px-4 rounded-xl glass border border-border hover:border-primary/30 hover:bg-accent transition-all gap-2"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-primary" />
                    <span className="text-xs font-medium">Query Plan</span>
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => toast.success("Data")}
                    className="h-9 px-4 rounded-xl glass border border-border hover:border-primary/30 hover:bg-accent transition-all gap-2"
                  >
                    <Table className="w-3.5 h-3.5 text-primary" />
                    <span className="text-xs font-medium">Data</span>
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => toast.success("Schema Context")}
                    className="h-9 px-4 rounded-xl glass border border-border hover:border-primary/30 hover:bg-accent transition-all gap-2"
                  >
                    <Settings className="w-3.5 h-3.5 text-primary" />
                    <span className="text-xs font-medium">Schema Context</span>
                  </Button>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="chat"
                initial={{ opacity: 0, x: 50 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -50 }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                className="absolute inset-0 z-20 flex flex-col pt-4"
              >
                <div className="max-w-3xl mx-auto w-full flex flex-col h-full px-6">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h2 className="text-2xl font-display font-bold">Chat</h2>
                      <p className="text-zinc-500 text-sm">Conversation with Kiwi</p>
                    </div>
                    <Button
                      variant="ghost"
                      onClick={() => setShowChat(false)}
                      className="h-10 w-10 rounded-xl glass border border-zinc-800/50 hover:border-green-500/30"
                    >
                      <ChevronLeft className="w-5 h-5" />
                    </Button>
                  </div>

                  <div
                    ref={scrollRef}
                    className="flex-1 overflow-y-auto space-y-6 pb-32 hide-scrollbar"
                  >
                    {messages.length === 0 ? (
                      <div className="h-64 flex flex-col items-center justify-center opacity-40">
                        <Sparkles className="w-12 h-12 mb-4 text-green-500/50" />
                        <p className="text-sm font-medium">Start a conversation with Kiwi</p>
                        <p className="text-xs text-zinc-600 mt-1">Use voice or type to begin</p>
                      </div>
                    ) : (
                      messages.map((msg) => (
                        <MessageBubble key={msg.id} message={msg} />
                      ))
                    )}
                    {isSpeaking && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex items-center gap-3 p-4 rounded-2xl bg-teal-500/5 border border-teal-500/10 max-w-[80%]"
                      >
                        <div className="flex gap-1">
                          {[0, 1, 2].map((i) => (
                            <motion.div
                              key={i}
                              animate={{ height: [4, 16, 4] }}
                              transition={{ duration: 0.5, repeat: Infinity, delay: i * 0.1 }}
                              className="w-1 bg-teal-400 rounded-full"
                            />
                          ))}
                        </div>
                        <span className="text-xs font-medium text-teal-400">Kiwi is typing...</span>
                      </motion.div>
                    )}
                  </div>
                </div>

                {/* Input Box with Voice and Send */}
                <div className="absolute bottom-6 left-0 right-0 px-6 pointer-events-none">
                  <div className="max-w-3xl mx-auto pointer-events-auto">
                    <div className="flex items-center gap-2 p-2 rounded-2xl glass border border-border bg-card/80 backdrop-blur-xl">
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
                        className="flex-1 bg-transparent border-0 focus-visible:ring-0 focus-visible:ring-offset-0 text-foreground placeholder:text-muted-foreground"
                      />
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={handleVoiceToggle}
                        className={`w-10 h-10 rounded-xl transition-all duration-300 flex items-center justify-center ${isRecording
                          ? 'bg-green-500 shadow-[0_0_30px_rgba(34,197,94,0.5)]'
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
                        onClick={() => {
                          if (inputMessage.trim()) {
                            handleSendMessage(inputMessage);
                            setInputMessage('');
                          }
                        }}
                        disabled={!inputMessage.trim()}
                        className={`w-10 h-10 rounded-xl transition-all duration-300 flex items-center justify-center ${inputMessage.trim()
                          ? 'bg-primary hover:bg-primary/90 shadow-[0_0_20px_rgba(var(--primary),0.3)]'
                          : 'bg-secondary border border-border opacity-50 cursor-not-allowed'
                          }`}
                      >
                        <Send className="w-5 h-5 text-white" />
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
