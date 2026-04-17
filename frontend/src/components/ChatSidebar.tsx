'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageCircle,
  Plus,
  Trash2,
  Pencil,
  Check,
  Search,
  PanelLeftClose,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import type { ChatTab } from '@/lib/types';

interface ChatSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  chatTabs: ChatTab[];
  activeChatId: string | null;
  onSwitchChat: (id: string) => void;
  onDeleteChat: (id: string) => void;
  onRenameChat: (id: string, title: string) => void;
  onNewChat: () => void;
  onOpenChat: () => void;
}

export function ChatSidebar({
  isOpen,
  onClose,
  chatTabs,
  activeChatId,
  onSwitchChat,
  onDeleteChat,
  onRenameChat,
  onNewChat,
  onOpenChat,
}: ChatSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [editingChatTitle, setEditingChatTitle] = useState('');

  const filteredChats = chatTabs.filter(tab =>
    tab.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    tab.messages.some(msg => msg.content.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const handleNewChat = () => {
    onNewChat();
    onClose();
    toast.success("New conversation started");
  };

  const handleSelectChat = (tabId: string, closeSidebar: boolean) => {
    if (editingChatId === tabId) return;
    onSwitchChat(tabId);
    onOpenChat();
    if (closeSidebar) onClose();
  };

  const handleFinishEditing = (tabId: string) => {
    onRenameChat(tabId, editingChatTitle);
    setEditingChatId(null);
    toast.success('Chat renamed');
  };

  // Shared sidebar header
  const sidebarHeader = (
    <div className="p-4 border-b border-border">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-bold font-display tracking-tight">Your Chats</h3>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Close sidebar"
          onClick={onClose}
          className="h-8 w-8 rounded-lg hover:bg-accent"
        >
          <PanelLeftClose className="w-4 h-4" />
        </Button>
      </div>
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
  );

  // Shared new chat button
  const newChatButton = (
    <div className="p-3">
      <Button
        onClick={handleNewChat}
        className="w-full h-10 bg-violet-600 hover:bg-violet-500 text-white rounded-lg font-semibold gap-2 transition-all"
      >
        <Plus className="w-4 h-4" />
        New Chat
      </Button>
    </div>
  );

  // Empty state
  const emptyState = (
    <div className="flex flex-col items-center justify-center h-32 opacity-40">
      <MessageCircle className="w-8 h-8 mb-2" />
      <p className="text-xs font-medium">
        {searchQuery ? 'No matching chats' : 'No conversations yet'}
      </p>
    </div>
  );

  return (
    <>
      {/* Mobile Sidebar Backdrop */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/50 z-40 md:hidden"
            onClick={onClose}
          />
        )}
      </AnimatePresence>

      {/* Desktop Sidebar - Width animation */}
      <motion.div
        initial={false}
        animate={{ width: isOpen ? 280 : 0 }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
        className="h-full overflow-hidden flex-shrink-0 hidden md:block"
      >
        <div className="w-[280px] h-full glass border-r border-border flex flex-col">
          {sidebarHeader}
          {newChatButton}
          <div className="flex-1 overflow-y-auto px-2 pb-4 hide-scrollbar">
            {filteredChats.length === 0 ? emptyState : (
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
                    onClick={() => handleSelectChat(tab.id, window.innerWidth < 768)}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        {editingChatId === tab.id ? (
                          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                            <Input
                              value={editingChatTitle}
                              onChange={(e) => setEditingChatTitle(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleFinishEditing(tab.id);
                                else if (e.key === 'Escape') setEditingChatId(null);
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
                                handleFinishEditing(tab.id);
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
                              onDeleteChat(tab.id);
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
        animate={{ x: isOpen ? 0 : '-100%' }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
        className="fixed md:hidden left-0 top-0 h-full z-50 w-[280px]"
      >
        <div className="w-full h-full glass border-r border-border flex flex-col bg-background">
          {sidebarHeader}
          {newChatButton}
          <div className="flex-1 overflow-y-auto px-2 pb-4 hide-scrollbar">
            {filteredChats.length === 0 ? emptyState : (
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
                    onClick={() => handleSelectChat(tab.id, true)}
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
    </>
  );
}
