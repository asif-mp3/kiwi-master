'use client';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  MessageCircle,
  Table,
  User,
  Settings,
  LogOut,
  MessageSquarePlus,
  Loader2,
  Sun,
  Moon,
  Monitor
} from 'lucide-react';
import { useTheme } from 'next-themes';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useState } from 'react';

interface ChatHeaderProps {
  username: string;
  chatTabsCount: number;
  isDatasetReady: boolean;
  isConnectionVerified: boolean;
  showChat: boolean;
  onShowChatsPanel: () => void;
  onOpenDatasetModal: () => void;
  onToggleChat: () => void;
  onLogout: () => void;
}

export function ChatHeader({
  username,
  chatTabsCount,
  isDatasetReady,
  isConnectionVerified,
  showChat,
  onShowChatsPanel,
  onOpenDatasetModal,
  onToggleChat,
  onLogout
}: ChatHeaderProps) {
  const { theme, setTheme } = useTheme();
  const [showSettings, setShowSettings] = useState(false);

  return (
    <>
      <header className="relative z-20 flex items-center justify-between px-6 py-5">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={onShowChatsPanel}
            className="h-11 px-4 rounded-xl glass border border-border hover:border-violet-500/30 hover:bg-accent transition-all gap-3"
          >
            <MessageSquarePlus className="w-4 h-4 text-violet-400" />
            <span className="text-sm font-medium">Your Chats</span>
            {chatTabsCount > 0 && (
              <span className="ml-1 px-2 py-0.5 text-xs font-bold bg-violet-500/20 text-violet-400 rounded-full">
                {chatTabsCount}
              </span>
            )}
          </Button>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            onClick={onOpenDatasetModal}
            className={cn(
              "h-11 px-4 rounded-xl glass border transition-all gap-2",
              isDatasetReady
                ? isConnectionVerified
                  ? "border-violet-500/50 bg-violet-500/10 text-violet-400 hover:bg-violet-500/20"
                  : "border-amber-500/50 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20"
                : "border-border hover:border-violet-500/30 hover:bg-accent"
            )}
          >
            {isDatasetReady && !isConnectionVerified ? (
              <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
            ) : (
              <Table className={cn("w-4 h-4", isDatasetReady ? "text-violet-400" : "text-zinc-400")} />
            )}

            <span className="text-sm font-medium hidden sm:inline">
              {isDatasetReady
                ? (isConnectionVerified ? 'Loaded Successfully' : 'Verifying...')
                : ''}
            </span>
          </Button>

          <Button
            variant="ghost"
            onClick={onToggleChat}
            className={`h-11 px-4 rounded-xl border transition-all gap-2 ${showChat
              ? 'bg-violet-500 text-white border-violet-400 hover:bg-violet-400'
              : 'glass border-border hover:border-violet-500/30 hover:bg-accent'
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
                className="h-11 w-11 rounded-xl glass border border-border hover:border-violet-500/30 hover:bg-accent transition-all"
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
    </>
  );
}
