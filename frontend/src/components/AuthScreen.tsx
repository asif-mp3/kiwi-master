'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, ArrowRight, KeyRound, Lock, Zap } from 'lucide-react';
import { toast } from 'sonner';

interface AuthScreenProps {
  onLogin: (username: string) => void;
}

export function AuthScreen({ onLogin }: AuthScreenProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(false);
  const [focusedField, setFocusedField] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(false);

    await new Promise((resolve) => setTimeout(resolve, 1800));

    if (username === 'admin' && password === 'admin123') {
      onLogin(username);
      toast.success('Welcome to Kiwi', {
        description: 'Your session has been authenticated.',
      });
    } else {
      setError(true);
      toast.error('Access Denied', {
        description: 'Invalid credentials. Please try again.',
      });
      setIsLoading(false);
    }
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
        delayChildren: 0.2,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] },
    },
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#09090b] p-6 relative overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <motion.div 
          animate={{ 
            scale: [1, 1.2, 1],
            opacity: [0.08, 0.15, 0.08],
            x: [0, 50, 0],
            y: [0, -30, 0]
          }}
          transition={{ repeat: Infinity, duration: 15, ease: "easeInOut" }}
          className="absolute top-[-20%] left-[-15%] w-[700px] h-[700px] bg-green-500 rounded-full blur-[200px]" 
        />
        <motion.div 
          animate={{ 
            scale: [1, 1.3, 1],
            opacity: [0.05, 0.1, 0.05],
            x: [0, -40, 0],
            y: [0, 40, 0]
          }}
          transition={{ repeat: Infinity, duration: 18, ease: "easeInOut", delay: 2 }}
          className="absolute bottom-[-20%] right-[-15%] w-[700px] h-[700px] bg-teal-500 rounded-full blur-[200px]" 
        />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,#09090b_70%)]" />
      </div>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="w-full max-w-md space-y-10 relative z-10"
      >
        {/* Logo & Header */}
        <div className="text-center space-y-6">
          <motion.div
            variants={itemVariants}
            className="inline-flex items-center justify-center"
          >
            <motion.div 
              whileHover={{ scale: 1.05, rotate: 5 }}
              className="w-20 h-20 rounded-3xl bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center shadow-2xl shadow-green-500/30 relative overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent" />
              <span className="text-4xl font-black text-white relative z-10 font-display">K</span>
            </motion.div>
          </motion.div>
          
          <div className="space-y-2">
            <motion.h1 
              variants={itemVariants}
              className="text-5xl font-black tracking-tight text-white font-display"
            >
              Welcome to <span className="gradient-text">Kiwi</span>
            </motion.h1>
            <motion.p 
              variants={itemVariants}
              className="text-zinc-500 text-sm font-medium tracking-wide"
            >
              RAG-powered voice assistant for your data
            </motion.p>
          </div>
        </div>

        {/* Login Form */}
        <motion.div
          variants={itemVariants}
          className="glass rounded-3xl p-8 border border-zinc-800/50 relative overflow-hidden"
        >
          {/* Top Accent */}
          <div className="absolute top-0 left-8 right-8 h-px bg-gradient-to-r from-transparent via-green-500/50 to-transparent" />
          
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label 
                htmlFor="username" 
                className={`text-[10px] uppercase tracking-[0.3em] font-bold transition-colors ${
                  focusedField === 'username' ? 'text-green-400' : 'text-zinc-500'
                }`}
              >
                Username
              </Label>
              <div className="relative group">
                <motion.div
                  animate={{ 
                    opacity: focusedField === 'username' ? 1 : 0,
                    scale: focusedField === 'username' ? 1 : 0.95
                  }}
                  className="absolute -inset-0.5 bg-gradient-to-r from-green-500/20 to-teal-500/20 rounded-xl blur-sm"
                />
                <Input
                  id="username"
                  type="text"
                  placeholder="admin"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  onFocus={() => setFocusedField('username')}
                  onBlur={() => setFocusedField(null)}
                  className={`relative h-14 bg-zinc-900/80 border-zinc-800 rounded-xl focus-visible:ring-green-500/50 focus-visible:border-green-500/50 transition-all text-white placeholder:text-zinc-600 pl-12 ${
                    error ? 'border-red-500/50 focus-visible:ring-red-500/30' : ''
                  }`}
                  disabled={isLoading}
                />
                <KeyRound className={`absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 transition-colors ${
                  focusedField === 'username' ? 'text-green-400' : 'text-zinc-600'
                }`} />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label 
                htmlFor="password" 
                className={`text-[10px] uppercase tracking-[0.3em] font-bold transition-colors ${
                  focusedField === 'password' ? 'text-green-400' : 'text-zinc-500'
                }`}
              >
                Password
              </Label>
              <div className="relative group">
                <motion.div
                  animate={{ 
                    opacity: focusedField === 'password' ? 1 : 0,
                    scale: focusedField === 'password' ? 1 : 0.95
                  }}
                  className="absolute -inset-0.5 bg-gradient-to-r from-green-500/20 to-teal-500/20 rounded-xl blur-sm"
                />
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onFocus={() => setFocusedField('password')}
                  onBlur={() => setFocusedField(null)}
                  className={`relative h-14 bg-zinc-900/80 border-zinc-800 rounded-xl focus-visible:ring-green-500/50 focus-visible:border-green-500/50 transition-all text-white placeholder:text-zinc-600 pl-12 ${
                    error ? 'border-red-500/50 focus-visible:ring-red-500/30' : ''
                  }`}
                  disabled={isLoading}
                />
                <Lock className={`absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 transition-colors ${
                  focusedField === 'password' ? 'text-green-400' : 'text-zinc-600'
                }`} />
              </div>
            </div>

            <motion.div
              whileHover={{ scale: isLoading ? 1 : 1.02 }}
              whileTap={{ scale: isLoading ? 1 : 0.98 }}
            >
              <Button
                type="submit"
                className="w-full h-14 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-500 hover:to-green-600 text-white rounded-xl transition-all duration-300 font-bold shadow-xl shadow-green-500/20"
                disabled={isLoading}
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <span className="flex items-center justify-center gap-3 uppercase tracking-widest text-sm">
                    Sign In <ArrowRight className="w-4 h-4" />
                  </span>
                )}
              </Button>
            </motion.div>
          </form>

          {/* Demo Credentials */}
          <div className="mt-8 pt-6 border-t border-zinc-800/50">
            <p className="text-center text-[10px] font-bold uppercase tracking-[0.3em] text-zinc-600 mb-4">Demo Credentials</p>
            <div className="flex gap-4">
              <div className="flex-1 p-3 rounded-xl bg-zinc-900/50 border border-zinc-800/50">
                <p className="text-[9px] font-bold uppercase tracking-widest text-zinc-500 mb-1">User</p>
                <p className="text-sm font-mono text-green-400">admin</p>
              </div>
              <div className="flex-1 p-3 rounded-xl bg-zinc-900/50 border border-zinc-800/50">
                <p className="text-[9px] font-bold uppercase tracking-widest text-zinc-500 mb-1">Pass</p>
                <p className="text-sm font-mono text-green-400">admin123</p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Footer */}
        <motion.div
          variants={itemVariants}
          className="flex items-center justify-center gap-6 opacity-40"
        >
          <div className="flex items-center gap-2">
            <Zap className="w-3 h-3 text-green-500" />
            <span className="text-[10px] font-bold uppercase tracking-widest">RAG Engine</span>
          </div>
          <div className="w-1 h-1 rounded-full bg-zinc-600" />
          <span className="text-[10px] font-bold uppercase tracking-widest">v2.0</span>
        </motion.div>
      </motion.div>
    </div>
  );
}
