'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Message, AuthState, AppConfig, MessageRole, ChatTab } from './types';
import type { DatasetState, LoadingStage, DatasetMetadata } from './dataset-types';
import * as api from './api';


const AUTH_KEY = 'kiwi_assistant_auth';
const CHAT_KEY = 'kiwi_assistant_chat';
const CONFIG_KEY = 'kiwi_assistant_config';
const CHAT_TABS_KEY = 'kiwi_assistant_tabs';

export function useAppState() {
  const [auth, setAuth] = useState<AuthState>({
    isAuthenticated: false,
    username: null,
  });

  const [messages, setMessages] = useState<Message[]>([]);
  const [chatTabs, setChatTabs] = useState<ChatTab[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [config, setConfig] = useState<AppConfig>({
    googleSheetUrl: null,
  });
  const [isInitializing, setIsInitializing] = useState(true);

  // Dataset state (NEW - with per-chat support)
  const [datasetState, setDatasetState] = useState<DatasetState>('NO_DATASET');
  const [currentLoadingStage, setCurrentLoadingStage] = useState<LoadingStage | null>(null);
  const [loadingStageMessage, setLoadingStageMessage] = useState<string>('');
  const [loadingStageTimestamp, setLoadingStageTimestamp] = useState<Date>(new Date());
  const [datasetMetadata, setDatasetMetadata] = useState<DatasetMetadata | null>(null);
  const [datasetError, setDatasetError] = useState<string | null>(null);
  const [inspectionMode, setInspectionMode] = useState<boolean>(false);
  const [sheetUrl, setSheetUrl] = useState<string>('');
  const [sheetUrlLocked, setSheetUrlLocked] = useState<boolean>(false);

  // Voice state (NEW)
  const [voiceEnabled, setVoiceEnabled] = useState<boolean>(false);
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  // Per-chat dataset mapping (NEW - CRITICAL for dataset-lock-per-chat)
  const [chatDatasets, setChatDatasets] = useState<Record<string, {
    datasetState: DatasetState;
    metadata: DatasetMetadata | null;
    sheetUrl: string;
  }>>({});

  const eventSourceRef = useRef<EventSource | null>(null);



  useEffect(() => {
    const savedAuth = localStorage.getItem(AUTH_KEY);
    const savedChat = localStorage.getItem(CHAT_KEY);
    const savedConfig = localStorage.getItem(CONFIG_KEY);
    const savedTabs = localStorage.getItem(CHAT_TABS_KEY);

    if (savedAuth) {
      setAuth(JSON.parse(savedAuth));
    }

    if (savedChat) {
      setMessages(JSON.parse(savedChat));
    }

    if (savedConfig) {
      setConfig(JSON.parse(savedConfig));
    }

    if (savedTabs) {
      const tabs = JSON.parse(savedTabs);
      setChatTabs(tabs);
      if (tabs.length > 0) {
        const initialChatId = tabs[0].id;
        setActiveChatId(initialChatId);

        // RESTORE DATASET STATE for initial chat (Fixing persistence/refresh issue)
        // This duplicates logic from switchChat but is necessary for initialization
        const initialChat = tabs.find((t: ChatTab) => t.id === initialChatId);
        if (initialChat?.sheetUrl) {
          setSheetUrl(initialChat.sheetUrl);
          setSheetUrlLocked(true);
          setDatasetState('NO_DATASET'); // Will trigger auto-connect in UI
          console.log('Restored persisted sheet URL on mount:', initialChat.sheetUrl);
        }
      }
    }

    setIsInitializing(false);
  }, []);

  useEffect(() => {
    if (!isInitializing) {
      localStorage.setItem(AUTH_KEY, JSON.stringify(auth));
    }
  }, [auth, isInitializing]);

  useEffect(() => {
    if (!isInitializing) {
      localStorage.setItem(CHAT_KEY, JSON.stringify(messages));
    }
  }, [messages, isInitializing]);

  useEffect(() => {
    if (!isInitializing) {
      localStorage.setItem(CONFIG_KEY, JSON.stringify(config));
    }
  }, [config, isInitializing]);

  useEffect(() => {
    if (!isInitializing) {
      localStorage.setItem(CHAT_TABS_KEY, JSON.stringify(chatTabs));
    }
  }, [chatTabs, isInitializing]);

  const login = (username: string) => {
    setAuth({ isAuthenticated: true, username });
  };

  const logout = () => {
    setAuth({ isAuthenticated: false, username: null });
    setMessages([]);
    setChatTabs([]);
    setActiveChatId(null);
    setConfig({ googleSheetUrl: null });
    localStorage.removeItem(AUTH_KEY);
    localStorage.removeItem(CHAT_KEY);
    localStorage.removeItem(CONFIG_KEY);
    localStorage.removeItem(CHAT_TABS_KEY);
  };

  const addMessage = (content: string, role: MessageRole = 'user') => {
    const newMessage: Message = {
      id: Math.random().toString(36).substring(7),
      role,
      content,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, newMessage]);

    if (activeChatId) {
      setChatTabs((prev) => prev.map((tab) =>
        tab.id === activeChatId
          ? { ...tab, messages: [...tab.messages, newMessage], updatedAt: Date.now() }
          : tab
      ));
    }
    return newMessage;
  };

  const createNewChat = (title?: string) => {
    const newChat: ChatTab = {
      id: Math.random().toString(36).substring(7),
      title: title || `Chat ${chatTabs.length + 1}`,
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    setChatTabs((prev) => [newChat, ...prev]);
    setActiveChatId(newChat.id);
    setMessages([]);

    // Reset dataset state for new chat (dataset-lock-per-chat)
    setDatasetState('NO_DATASET');
    setSheetUrlLocked(false);
    setDatasetMetadata(null);
    setVoiceEnabled(false);

    return newChat;
  };


  const switchChat = (chatId: string) => {
    const chat = chatTabs.find((t) => t.id === chatId);
    if (chat) {
      setActiveChatId(chatId);
      setMessages(chat.messages);

      // Restore dataset state for this chat (dataset-lock-per-chat)
      // Check ephemeral state first, then persisted state
      const chatDataset = chatDatasets[chatId];
      const persistedSheetUrl = chat.sheetUrl;

      if (chatDataset) {
        setDatasetState(chatDataset.datasetState);
        setDatasetMetadata(chatDataset.metadata);
        setSheetUrl(chatDataset.sheetUrl);
        setSheetUrlLocked(chatDataset.datasetState !== 'NO_DATASET');
        setVoiceEnabled(chatDataset.datasetState === 'LOCKED_FOR_QUERY');
      } else if (persistedSheetUrl) {
        // REHYDRATE from persistence!
        // We know this chat HAS a sheet, but it might not be loaded in backend yet
        setDatasetState('NO_DATASET'); // Will trigger re-connect prompt or auto-connect
        setSheetUrl(persistedSheetUrl);
        setSheetUrlLocked(true); // LOCK IT - it's permanently associated
        setVoiceEnabled(false);
      } else {
        // No dataset for this chat yet
        setDatasetState('NO_DATASET');
        setDatasetMetadata(null);
        setSheetUrl('');
        setSheetUrlLocked(false);
        setVoiceEnabled(false);
      }
    }
  };


  const deleteChat = (chatId: string) => {
    setChatTabs((prev) => prev.filter((t) => t.id !== chatId));
    if (activeChatId === chatId) {
      const remaining = chatTabs.filter((t) => t.id !== chatId);
      if (remaining.length > 0) {
        switchChat(remaining[0].id);
      } else {
        setActiveChatId(null);
        setMessages([]);
      }
    }
  };

  const clearChat = () => {
    setMessages([]);
    if (activeChatId) {
      setChatTabs((prev) => prev.map((tab) =>
        tab.id === activeChatId
          ? { ...tab, messages: [], updatedAt: Date.now() }
          : tab
      ));
    }
  };

  const setGoogleSheetUrl = (url: string | null) => {
    setConfig((prev) => ({ ...prev, googleSheetUrl: url }));
  };

  // Dataset management functions (NEW)
  const connectSheet = useCallback((url?: string) => {
    // Lock URL input
    setSheetUrlLocked(true);
    setDatasetState('LOADING');
    setDatasetError(null);
    setCurrentLoadingStage('VALIDATING_URL');
    setLoadingStageMessage('');
    setLoadingStageTimestamp(new Date());

    // Close existing connection if any
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Start SSE connection
    const eventSource = api.connectSheet(url);
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.stage === 'ERROR') {
          setDatasetState('ERROR');
          setDatasetError(data.error || 'Unknown error');
          setCurrentLoadingStage('ERROR');
          eventSource.close();
          return;
        }

        setCurrentLoadingStage(data.stage);
        setLoadingStageMessage(data.message || '');
        setLoadingStageTimestamp(new Date());

        if (data.stage === 'READY') {
          setDatasetState('READY_FOR_INSPECTION');
          eventSource.close();
        }
      } catch (error) {
        console.error('Failed to parse SSE message:', error);
      }
    };

    eventSource.onerror = () => {
      setDatasetState('ERROR');
      setDatasetError('Connection lost. Check API server.');
      eventSource.close();
    };
  }, []);

  const loadInspection = useCallback(async () => {
    try {
      const metadata = await api.getSheetsSummary();
      setDatasetMetadata(metadata);
      setInspectionMode(true);

      // Store dataset for current chat (dataset-lock-per-chat)
      if (activeChatId) {
        setChatDatasets(prev => ({
          ...prev,
          [activeChatId]: {
            datasetState: 'READY_FOR_INSPECTION',
            metadata,
            sheetUrl
          }
        }));
      }
    } catch (error: any) {
      setDatasetError(error.message || 'Failed to load dataset summary');
    }
  }, [activeChatId, sheetUrl]);


  const closeInspection = useCallback(() => {
    setInspectionMode(false);
    // After viewing inspection, unlock chat/voice
    if (datasetState === 'READY_FOR_INSPECTION') {
      setDatasetState('LOCKED_FOR_QUERY');
      setVoiceEnabled(true); // Enable voice after dataset is locked

      // Update dataset state for current chat
      if (activeChatId) {
        setChatDatasets(prev => ({
          ...prev,
          [activeChatId]: {
            ...prev[activeChatId],
            datasetState: 'LOCKED_FOR_QUERY'
          }
        }));
      }
    }
  }, [datasetState, activeChatId]);

  const skipInspection = useCallback(() => {
    // Skip inspection and go directly to query mode
    setDatasetState('LOCKED_FOR_QUERY');
    setVoiceEnabled(true); // Enable voice when skipping to query mode

    // Update dataset state for current chat
    if (activeChatId) {
      setChatDatasets(prev => ({
        ...prev,
        [activeChatId]: {
          datasetState: 'LOCKED_FOR_QUERY',
          metadata: null,
          sheetUrl
        }
      }));
    }
  }, [activeChatId, sheetUrl]);


  const resetSessionState = useCallback(async () => {
    try {
      await api.resetSession();

      // Reset all dataset state
      setDatasetState('NO_DATASET');
      setCurrentLoadingStage(null);
      setLoadingStageMessage('');
      setDatasetMetadata(null);
      setDatasetError(null);
      setInspectionMode(false);
      setSheetUrlLocked(false);

      // Close SSE if open
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      // Create new chat
      createNewChat('New Chat');
    } catch (error: any) {
      console.error('Failed to reset session:', error);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);


  return {
    auth,
    messages,
    config,
    chatTabs,
    activeChatId,
    isInitializing,
    login,
    logout,
    addMessage,
    setMessages,
    setGoogleSheetUrl,
    createNewChat,
    switchChat,
    deleteChat,
    clearChat,
    // Dataset state (NEW)
    datasetState,
    currentLoadingStage,
    loadingStageMessage,
    loadingStageTimestamp,
    datasetMetadata,
    datasetError,
    inspectionMode,
    sheetUrl,
    sheetUrlLocked,
    setSheetUrl,
    connectSheet,
    loadInspection,
    closeInspection,
    skipInspection,
    resetSessionState,
    updateChatSheet: (chatId: string, sheetUrl: string, sheetName: string) => {
      // 1. Update ephemeral state
      setChatDatasets(prev => ({
        ...prev,
        [chatId]: {
          datasetState: 'READY_FOR_INSPECTION',
          metadata: null,
          sheetUrl
        }
      }));
      // 2. Update PERSISTED state (chatTabs)
      setChatTabs(prev => prev.map(tab =>
        tab.id === chatId ? { ...tab, sheetName, sheetUrl } : tab
      ));
    },
    // Voice state (NEW)
    voiceEnabled,
    setVoiceEnabled,
    isRecording,
    setIsRecording,
    isPlaying,
    setIsPlaying,
    // Per-chat datasets (NEW)
    chatDatasets,
  };
}
