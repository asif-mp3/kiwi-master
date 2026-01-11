'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { MessageCircle, X, Plus, Trash2 } from 'lucide-react';
import { ChatTab } from '@/lib/types';

interface ChatsSidebarProps {
  isOpen: boolean;
  chatTabs: ChatTab[];
  activeChatId: string | null;
  onClose: () => void;
  onNewChat: () => void;
  onSwitchChat: (chatId: string) => void;
  onDeleteChat: (chatId: string) => void;
}

export function ChatsSidebar({
  isOpen,
  chatTabs,
  activeChatId,
  onClose,
  onNewChat,
  onSwitchChat,
  onDeleteChat
}: ChatsSidebarProps) {
  return (
    <>
      <AnimatePresence>
        {isOpen && (
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
                  onClick={onClose}
                  className="h-9 w-9 rounded-xl hover:bg-zinc-800"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>

            <div className="p-4">
              <Button
                onClick={onNewChat}
                className="w-full h-12 bg-violet-600 hover:bg-violet-500 text-white rounded-xl font-semibold gap-2 transition-all hover:scale-[1.02] active:scale-[0.98]"
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
                        ? 'bg-violet-500/10 border border-violet-500/20'
                        : 'hover:bg-zinc-800/50 border border-transparent'
                        }`}
                      onClick={() => onSwitchChat(tab.id)}
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
                            onDeleteChat(tab.id);
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

      {/* Overlay */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm z-40"
          />
        )}
      </AnimatePresence>
    </>
  );
}
