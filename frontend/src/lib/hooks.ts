'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Message, AuthState, AppConfig, MessageRole, ChatTab } from './types';
import { STORAGE_KEYS } from '../config/storage-keys';
import { SESSION } from '../config/timing';
import { DEFAULT_SESSION_NAME } from './constants';

const AUTH_KEY = STORAGE_KEYS.AUTH;
const CHAT_KEY = STORAGE_KEYS.CHAT;
const CONFIG_KEY = STORAGE_KEYS.CONFIG;
const CHAT_TABS_KEY = STORAGE_KEYS.TABS;
const SESSION_LAST_ACTIVITY_KEY = STORAGE_KEYS.LAST_ACTIVITY;
const SESSION_NAME_KEY = STORAGE_KEYS.SESSION_NAME;

const SESSION_TIMEOUT_MS = SESSION.TIMEOUT_MS;

// Max messages to persist per chat tab (prevents localStorage quota overflow)
const MAX_PERSISTED_MESSAGES = 50;

/** Wrap localStorage.setItem — catches QuotaExceededError instead of crashing. */
function safeSetItem(key: string, value: string): boolean {
  try {
    localStorage.setItem(key, value);
    return true;
  } catch {
    console.error(`localStorage quota exceeded for key "${key}" (${(value.length / 1024).toFixed(0)}KB)`);
    return false;
  }
}

/** Strip heavy metadata.data from older messages and cap per-chat message count. */
function trimForStorage(tabs: ChatTab[]): ChatTab[] {
  return tabs.map(tab => ({
    ...tab,
    messages: tab.messages
      .slice(-MAX_PERSISTED_MESSAGES)
      .map((msg, idx, arr) => {
        // Keep full metadata on the last 5 messages (recent context)
        if (idx >= arr.length - 5 || !msg.metadata?.data) return msg;
        // Strip data rows from older messages — they can be huge
        const { data, ...restMeta } = msg.metadata;
        return { ...msg, metadata: restMeta };
      }),
  }));
}

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

  // Session-based name for "Call me X" feature - defaults to "Boss", clears on timeout
  const [sessionName, setSessionNameState] = useState<string>(DEFAULT_SESSION_NAME);

  useEffect(() => {
    // Safe JSON parse helper - returns null on error and clears corrupted data
    const safeJsonParse = <T>(key: string): T | null => {
      try {
        const data = localStorage.getItem(key);
        if (!data) return null;
        return JSON.parse(data) as T;
      } catch {
        localStorage.removeItem(key);
        return null;
      }
    };

    // SECURITY: Validate access token exists and is valid format (64 char hex)
    const validateToken = (): boolean => {
      const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
      if (!token) return false;
      // Token must be 64 character hex string (SHA256 hash)
      if (token.length !== 64) return false;
      if (!/^[0-9a-f]+$/.test(token)) return false;
      return true;
    };

    // Clear all auth data if token is invalid
    const clearAllAuthData = () => {
      localStorage.removeItem(AUTH_KEY);
      localStorage.removeItem(CONFIG_KEY);
      localStorage.removeItem(CHAT_TABS_KEY);
      localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
      localStorage.removeItem(SESSION_LAST_ACTIVITY_KEY);
    };

    // Check if session has expired due to inactivity
    const isSessionExpired = (): boolean => {
      const lastActivity = localStorage.getItem(SESSION_LAST_ACTIVITY_KEY);
      if (!lastActivity) {
        return true;
      }
      const lastActivityTime = parseInt(lastActivity, 10);
      if (isNaN(lastActivityTime)) {
        return true;
      }
      const now = Date.now();
      const elapsed = now - lastActivityTime;
      const isExpired = elapsed > SESSION_TIMEOUT_MS;
      return isExpired;
    };

    // CRITICAL: Only restore auth if valid token exists AND session not expired
    const tokenValid = validateToken();
    const sessionExpired = isSessionExpired();

    if (!tokenValid || sessionExpired) {
      clearAllAuthData();
      setIsInitializing(false);
      return;
    }

    const savedAuth = safeJsonParse<AuthState>(AUTH_KEY);
    const savedConfig = safeJsonParse<AppConfig>(CONFIG_KEY);
    const savedTabs = safeJsonParse<ChatTab[]>(CHAT_TABS_KEY);

    if (savedAuth) {
      setAuth(savedAuth);
    }

    if (savedConfig) {
      setConfig(savedConfig);
    }

    if (savedTabs && Array.isArray(savedTabs)) {
      setChatTabs(savedTabs);
      if (savedTabs.length > 0) {
        setActiveChatId(savedTabs[0].id);
        // Load messages from the active tab (single source of truth)
        setMessages(savedTabs[0].messages);
      }
    }

    // Migrate: remove legacy CHAT_KEY if still present
    localStorage.removeItem(CHAT_KEY);

    // Load session name (for "Call me X" feature)
    const savedSessionName = localStorage.getItem(SESSION_NAME_KEY);
    if (savedSessionName) {
      setSessionNameState(savedSessionName);
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
        handleSessionTimeout();
        return;
      }
      const lastActivityTime = parseInt(lastActivity, 10);
      if (isNaN(lastActivityTime)) {
        handleSessionTimeout();
        return;
      }
      const now = Date.now();
      const elapsed = now - lastActivityTime;
      if (elapsed > SESSION_TIMEOUT_MS) {
        handleSessionTimeout();
      }
    };

    const handleSessionTimeout = () => {
      // Clear all auth data
      localStorage.removeItem(AUTH_KEY);
      localStorage.removeItem(CONFIG_KEY);
      localStorage.removeItem(CHAT_TABS_KEY);
      localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
      localStorage.removeItem(SESSION_LAST_ACTIVITY_KEY);
      localStorage.removeItem(SESSION_NAME_KEY); // Clear "Call me X" name
      // Reset state
      setAuth({ isAuthenticated: false, username: null });
      setMessages([]);
      setChatTabs([]);
      setActiveChatId(null);
      setConfig({ googleSheetUrl: null });
      setSessionNameState(DEFAULT_SESSION_NAME); // Reset to default
    };

    // Set initial activity timestamp on login
    updateActivity();

    // Track user activity events
    const activityEvents = ['click', 'keydown', 'mousemove', 'scroll', 'touchstart'];

    // Throttle activity updates to avoid excessive writes (max once per 10 seconds)
    let lastUpdate = Date.now();
    const throttledUpdateActivity = () => {
      const now = Date.now();
      if (now - lastUpdate > SESSION.ACTIVITY_THROTTLE_MS) {
        updateActivity();
        lastUpdate = now;
      }
    };

    // Add event listeners
    activityEvents.forEach(event => {
      window.addEventListener(event, throttledUpdateActivity, { passive: true });
    });

    const expiryCheckInterval = setInterval(checkSessionExpiry, SESSION.EXPIRY_CHECK_INTERVAL_MS);

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

  // Messages are stored ONLY inside chatTabs (single source of truth).
  // No separate CHAT_KEY persistence — that caused double-storage and quota overflow.

  useEffect(() => {
    if (!isInitializing) {
      safeSetItem(CONFIG_KEY, JSON.stringify(config));
    }
  }, [config, isInitializing]);

  useEffect(() => {
    if (!isInitializing) {
      const trimmed = trimForStorage(chatTabs);
      if (!safeSetItem(CHAT_TABS_KEY, JSON.stringify(trimmed))) {
        // Last resort: keep only the 3 most recent chats
        const reduced = trimForStorage(chatTabs.slice(0, 3));
        safeSetItem(CHAT_TABS_KEY, JSON.stringify(reduced));
      }
    }
  }, [chatTabs, isInitializing]);

  const login = (username: string) => {
    // Set activity timestamp on login
    localStorage.setItem(SESSION_LAST_ACTIVITY_KEY, Date.now().toString());
    setAuth({ isAuthenticated: true, username });
  };

  const setUsername = (newName: string) => {
    // Update username (for "call me X" feature) - SESSION ONLY
    // Deliberately NOT persisting to localStorage so it resets to "Boss" on logout/timeout
    setAuth(prev => ({ ...prev, username: newName }));
  };

  // Set session name for "Call me X" feature - persists until session timeout
  const setSessionName = (name: string) => {
    setSessionNameState(name);
    localStorage.setItem(SESSION_NAME_KEY, name);
  };

  const logout = () => {
    setAuth({ isAuthenticated: false, username: null });
    setMessages([]);
    setChatTabs([]);
    setActiveChatId(null);
    setConfig({ googleSheetUrl: null });
    setSessionNameState(DEFAULT_SESSION_NAME); // Reset to default
    localStorage.removeItem(AUTH_KEY);
    localStorage.removeItem(CONFIG_KEY);
    localStorage.removeItem(CHAT_TABS_KEY);
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(SESSION_LAST_ACTIVITY_KEY);
    localStorage.removeItem(SESSION_NAME_KEY);
  };

  const addMessage = (content: string, role: MessageRole = 'user', metadata?: Message['metadata'], targetChatId?: string) => {
    const newMessage: Message = {
      id: Math.random().toString(36).substring(7),
      role,
      content,
      timestamp: Date.now(),
      metadata,
    };
    setMessages((prev) => [...prev, newMessage]);

    // Use explicit targetChatId if provided, otherwise fall back to activeChatId
    // This fixes the race condition when creating a new chat and immediately adding a message
    const chatIdToUse = targetChatId || activeChatId;
    if (chatIdToUse) {
      setChatTabs((prev) => prev.map((tab) =>
        tab.id === chatIdToUse
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

  const clearCurrentChat = async () => {
    if (!activeChatId) return;

    // Clear messages but keep the chat tab, dataset connection, and session name
    setMessages([]);
    setChatTabs((prev) =>
      prev.map((tab) =>
        tab.id === activeChatId
          ? { ...tab, messages: [], updatedAt: Date.now() }
          : tab
      )
    );

    // Clear backend caches (query cache, context)
    try {
      const { api } = await import('../services/api');
      await api.clearCache();
    } catch {
      // Error handled silently
    }
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
    sessionName, // "Call me X" name - defaults to "Boss"
    login,
    logout,
    setUsername,
    setSessionName, // Set "Call me X" name
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
