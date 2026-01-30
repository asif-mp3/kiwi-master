'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Message, AuthState, AppConfig, MessageRole, ChatTab } from './types';

const AUTH_KEY = 'thara_auth';
const CHAT_KEY = 'thara_chat';
const CONFIG_KEY = 'thara_config';
const CHAT_TABS_KEY = 'thara_tabs';
const SESSION_LAST_ACTIVITY_KEY = 'thara_last_activity';

// Session timeout: 300 seconds (5 minutes) of inactivity
const SESSION_TIMEOUT_MS = 300 * 1000;

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
      localStorage.removeItem(SESSION_LAST_ACTIVITY_KEY);
    };

    // Check if session has expired due to inactivity
    const isSessionExpired = (): boolean => {
      const lastActivity = localStorage.getItem(SESSION_LAST_ACTIVITY_KEY);
      if (!lastActivity) return true; // No activity recorded = expired
      const lastActivityTime = parseInt(lastActivity, 10);
      if (isNaN(lastActivityTime)) return true;
      const now = Date.now();
      return (now - lastActivityTime) > SESSION_TIMEOUT_MS;
    };

    // CRITICAL: Only restore auth if valid token exists AND session not expired
    if (!validateToken() || isSessionExpired()) {
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

  // Activity tracking for session timeout
  useEffect(() => {
    if (!auth.isAuthenticated) return;

    // Update last activity timestamp
    const updateActivity = () => {
      localStorage.setItem(SESSION_LAST_ACTIVITY_KEY, Date.now().toString());
    };

    // Check if session expired and logout if so
    const checkSessionExpiry = () => {
      const lastActivity = localStorage.getItem(SESSION_LAST_ACTIVITY_KEY);
      if (!lastActivity) {
        // No activity recorded while authenticated - logout
        handleSessionTimeout();
        return;
      }
      const lastActivityTime = parseInt(lastActivity, 10);
      if (isNaN(lastActivityTime)) {
        handleSessionTimeout();
        return;
      }
      const now = Date.now();
      if ((now - lastActivityTime) > SESSION_TIMEOUT_MS) {
        handleSessionTimeout();
      }
    };

    const handleSessionTimeout = () => {
      console.log('[Session] Timeout due to inactivity - logging out');
      // Clear all auth data
      localStorage.removeItem(AUTH_KEY);
      localStorage.removeItem(CHAT_KEY);
      localStorage.removeItem(CONFIG_KEY);
      localStorage.removeItem(CHAT_TABS_KEY);
      localStorage.removeItem('thara_access_token');
      localStorage.removeItem(SESSION_LAST_ACTIVITY_KEY);
      // Reset state
      setAuth({ isAuthenticated: false, username: null });
      setMessages([]);
      setChatTabs([]);
      setActiveChatId(null);
      setConfig({ googleSheetUrl: null });
    };

    // Set initial activity timestamp on login
    updateActivity();

    // Track user activity events
    const activityEvents = ['click', 'keydown', 'mousemove', 'scroll', 'touchstart'];

    // Throttle activity updates to avoid excessive writes (max once per 10 seconds)
    let lastUpdate = Date.now();
    const throttledUpdateActivity = () => {
      const now = Date.now();
      if (now - lastUpdate > 10000) { // 10 seconds throttle
        updateActivity();
        lastUpdate = now;
      }
    };

    // Add event listeners
    activityEvents.forEach(event => {
      window.addEventListener(event, throttledUpdateActivity, { passive: true });
    });

    // Check session expiry every 30 seconds
    const expiryCheckInterval = setInterval(checkSessionExpiry, 30000);

    // Cleanup
    return () => {
      activityEvents.forEach(event => {
        window.removeEventListener(event, throttledUpdateActivity);
      });
      clearInterval(expiryCheckInterval);
    };
  }, [auth.isAuthenticated]);

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
    // Set activity timestamp on login
    localStorage.setItem(SESSION_LAST_ACTIVITY_KEY, Date.now().toString());
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
    localStorage.removeItem(SESSION_LAST_ACTIVITY_KEY);
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
