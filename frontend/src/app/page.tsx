'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { useAppState } from '@/lib/hooks';
import { AuthScreen } from '@/components/AuthScreen';
import { ChatScreen } from '@/components/ChatScreen';
import { Loader2 } from 'lucide-react';

export default function Home() {
  const { auth, login, logout, isInitializing } = useAppState();

  if (isInitializing) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-zinc-50 dark:bg-zinc-950">
        <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <main className="relative h-screen w-full overflow-hidden bg-zinc-50 dark:bg-zinc-950">
      <AnimatePresence mode="wait">
        {!auth.isAuthenticated ? (
          <motion.div
            key="auth"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 1.05, filter: 'blur(10px)' }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="h-full w-full"
          >
            <AuthScreen onLogin={login} />
          </motion.div>
        ) : (
          <motion.div
            key="chat"
            initial={{ opacity: 0, scale: 0.95, filter: 'blur(10px)' }}
            animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="h-full w-full"
          >
            <ChatScreen onLogout={logout} username={auth.username || 'Executive'} />
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
