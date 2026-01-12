'use client';

import { useState, useEffect } from 'react';
import { Message, AuthState, AppConfig, MessageRole, ChatTab } from './types';

const AUTH_KEY = 'thara_auth';
const CHAT_KEY = 'thara_chat';
const CONFIG_KEY = 'thara_config';
const CHAT_TABS_KEY = 'thara_tabs';

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

  useEffect(() => {
    // Safe JSON parse helper - returns null on error and clears corrupted data
    const safeJsonParse = <T>(key: string): T | null => {
      try {
        const data = localStorage.getItem(key);
        if (!data) return null;
        return JSON.parse(data) as T;
      } catch (e) {
        console.warn(`[Storage] Corrupted data for ${key}, clearing...`);
        localStorage.removeItem(key);
        return null;
      }
    };

    // SECURITY: Validate access token exists and is valid format (64 char hex)
    const validateToken = (): boolean => {
      const token = localStorage.getItem('thara_access_token');
      if (!token) return false;
      // Token must be 64 character hex string (SHA256 hash)
      if (token.length !== 64) return false;
      if (!/^[0-9a-f]+$/.test(token)) return false;
      return true;
    };

    // Clear all auth data if token is invalid
    const clearAllAuthData = () => {
      localStorage.removeItem(AUTH_KEY);
      localStorage.removeItem(CHAT_KEY);
      localStorage.removeItem(CONFIG_KEY);
      localStorage.removeItem(CHAT_TABS_KEY);
      localStorage.removeItem('thara_access_token');
    };

    // CRITICAL: Only restore auth if valid token exists
    if (!validateToken()) {
      clearAllAuthData();
      setIsInitializing(false);
      return;
    }

    const savedAuth = safeJsonParse<AuthState>(AUTH_KEY);
    const savedChat = safeJsonParse<Message[]>(CHAT_KEY);
    const savedConfig = safeJsonParse<AppConfig>(CONFIG_KEY);
    const savedTabs = safeJsonParse<ChatTab[]>(CHAT_TABS_KEY);

    if (savedAuth) {
      setAuth(savedAuth);
    }

    if (savedChat && Array.isArray(savedChat)) {
      setMessages(savedChat);
    }

    if (savedConfig) {
      setConfig(savedConfig);
    }

    if (savedTabs && Array.isArray(savedTabs)) {
      setChatTabs(savedTabs);
      if (savedTabs.length > 0) {
        setActiveChatId(savedTabs[0].id);
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
    localStorage.removeItem('thara_access_token');
  };

  const addMessage = (content: string, role: MessageRole = 'user', metadata?: Message['metadata']) => {
    const newMessage: Message = {
      id: Math.random().toString(36).substring(7),
      role,
      content,
      timestamp: Date.now(),
      metadata,
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
      datasetUrl: null,
      datasetStatus: 'unconnected',
    };
    setChatTabs((prev) => [newChat, ...prev]);
    setActiveChatId(newChat.id);
    setMessages([]);
    return newChat;
  };

  const switchChat = (chatId: string) => {
    const chat = chatTabs.find((t) => t.id === chatId);
    if (chat) {
      setActiveChatId(chatId);
      setMessages(chat.messages);
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

  const renameChat = (chatId: string, newTitle: string) => {
    if (!newTitle.trim()) return;
    setChatTabs((prev) =>
      prev.map((tab) =>
        tab.id === chatId
          ? { ...tab, title: newTitle.trim(), updatedAt: Date.now() }
          : tab
      )
    );
  };

  const setDatasetForChat = (
    url: string | null,
    status: ChatTab['datasetStatus'] = 'unconnected',
    stats?: ChatTab['datasetStats'],
    targetChatId?: string // Optional: specify which chat to update
  ) => {
    const chatIdToUpdate = targetChatId || activeChatId;
    if (!chatIdToUpdate) {
      console.warn('[setDatasetForChat] No active chat to update');
      return;
    }

    setChatTabs((prev) =>
      prev.map((tab) =>
        tab.id === chatIdToUpdate
          ? {
            ...tab,
            datasetUrl: url,
            datasetStatus: status,
            datasetStats: stats,
            updatedAt: Date.now(),
          }
          : tab
      )
    );
  };

  const updateMessage = (messageId: string, updates: Partial<Message>) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === messageId ? { ...msg, ...updates } : msg))
    );

    if (activeChatId) {
      setChatTabs((prev) =>
        prev.map((tab) =>
          tab.id === activeChatId
            ? {
              ...tab,
              messages: tab.messages.map((msg) =>
                msg.id === messageId ? { ...msg, ...updates } : msg
              ),
              updatedAt: Date.now(),
            }
            : tab
        )
      );
    }
  };

  const getCurrentChat = () => {
    return chatTabs.find((tab) => tab.id === activeChatId);
  };

  const clearCurrentChat = () => {
    if (!activeChatId) return;

    // Clear messages but keep the chat tab and dataset connection
    setMessages([]);
    setChatTabs((prev) =>
      prev.map((tab) =>
        tab.id === activeChatId
          ? { ...tab, messages: [], updatedAt: Date.now() }
          : tab
      )
    );
  };

  const setGoogleSheetUrl = (url: string | null) => {
    setConfig((prev) => ({ ...prev, googleSheetUrl: url }));
  };

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
    renameChat,
    setDatasetForChat,
    getCurrentChat,
    updateMessage,
    clearCurrentChat,
  };
}
