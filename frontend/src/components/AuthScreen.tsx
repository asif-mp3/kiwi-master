'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Loader2, Sparkles, Database, MessageSquare, Mic, User, Lock, Eye, EyeOff } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '@/services/api';

interface AuthScreenProps {
  onLogin: (username: string) => void;
}

export function AuthScreen({ onLogin }: AuthScreenProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [userId, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!userId.trim() || !password.trim()) {
      toast.error('Please enter both User ID and Password');
      return;
    }

    setIsLoading(true);

    try {
      const result = await api.login(userId, password);

      if (result.success && result.user) {
        // Store auth state
        localStorage.setItem('thara_auth', JSON.stringify({
          isAuthenticated: true,
          username: result.user.name,
        }));
        toast.success('Welcome back!', {
          description: `Signed in as ${result.user.name}`,
        });
        onLogin(result.user.name);
      } else {
        toast.error('Login Failed', {
          description: result.error || 'Invalid credentials',
        });
      }
    } catch (err) {
      console.error('Login error:', err);
      toast.error('Login Failed', {
        description: 'Unable to connect to server. Please try again.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] },
    },
  };

  const features = [
    { icon: MessageSquare, label: 'Natural Language Queries' },
    { icon: Database, label: 'Google Sheets Integration' },
    { icon: Mic, label: 'Voice Enabled' },
  ];

  return (
    <div className="h-[100dvh] w-full bg-background flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.1, 0.15, 0.1],
          }}
          transition={{ repeat: Infinity, duration: 12, ease: "easeInOut" }}
          className="absolute top-1/4 -left-32 w-[500px] h-[500px] bg-violet-600 rounded-full blur-[150px]"
        />
        <motion.div
          animate={{
            scale: [1, 1.3, 1],
            opacity: [0.08, 0.12, 0.08],
          }}
          transition={{ repeat: Infinity, duration: 15, ease: "easeInOut", delay: 1 }}
          className="absolute -bottom-32 -right-32 w-[600px] h-[600px] bg-purple-600 rounded-full blur-[180px]"
        />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,var(--background)_70%)]" />
      </div>

      {/* Main Content */}
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="relative z-10 w-full max-w-md"
      >
        {/* Card */}
        <motion.div
          variants={itemVariants}
          className="bg-zinc-900/60 backdrop-blur-xl rounded-3xl border border-zinc-800/60 shadow-2xl overflow-hidden"
        >
          {/* Gradient Top Border */}
          <div className="h-1 bg-gradient-to-r from-violet-500 via-purple-500 to-violet-500" />

          <div className="p-8 sm:p-10">
            {/* Logo */}
            <motion.div
              variants={itemVariants}
              className="flex justify-center mb-8"
            >
              <motion.div
                whileHover={{ scale: 1.05, rotate: 3 }}
                transition={{ type: "spring", stiffness: 400 }}
                className="w-20 h-20 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-xl shadow-violet-500/25 relative"
              >
                <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-white/20 to-transparent" />
                <span className="text-4xl font-black text-white relative z-10">T</span>
              </motion.div>
            </motion.div>

            {/* Title */}
            <motion.div variants={itemVariants} className="text-center mb-8">
              <h1 className="text-3xl sm:text-4xl font-bold text-white mb-3">
                Welcome to{' '}
                <span className="bg-gradient-to-r from-violet-400 to-purple-400 bg-clip-text text-transparent">
                  Thara.ai
                </span>
              </h1>
              <p className="text-zinc-400 text-sm sm:text-base">
                Your AI-powered analytics assistant
              </p>
            </motion.div>

            {/* Features */}
            <motion.div
              variants={itemVariants}
              className="flex justify-center gap-6 mb-10"
            >
              {features.map((feature, index) => (
                <motion.div
                  key={feature.label}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 + index * 0.1 }}
                  className="flex flex-col items-center gap-2 group"
                >
                  <div className="w-10 h-10 rounded-xl bg-zinc-800/80 border border-zinc-700/50 flex items-center justify-center group-hover:border-violet-500/50 group-hover:bg-violet-500/10 transition-all duration-300">
                    <feature.icon className="w-5 h-5 text-zinc-400 group-hover:text-violet-400 transition-colors" />
                  </div>
                  <span className="text-[10px] text-zinc-500 font-medium text-center leading-tight max-w-[70px]">
                    {feature.label}
                  </span>
                </motion.div>
              ))}
            </motion.div>

            {/* Login Form */}
            <motion.form variants={itemVariants} onSubmit={handleLogin} className="space-y-4">
              {/* User ID Input */}
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <User className="w-5 h-5 text-zinc-500" />
                </div>
                <input
                  type="text"
                  value={userId}
                  onChange={(e) => setUserId(e.target.value)}
                  placeholder="User ID"
                  disabled={isLoading}
                  className="w-full h-12 pl-12 pr-4 bg-zinc-800/60 border border-zinc-700/50 rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 transition-all disabled:opacity-50"
                />
              </div>

              {/* Password Input */}
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Lock className="w-5 h-5 text-zinc-500" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                  disabled={isLoading}
                  className="w-full h-12 pl-12 pr-12 bg-zinc-800/60 border border-zinc-700/50 rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 transition-all disabled:opacity-50"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-4 flex items-center text-zinc-500 hover:text-violet-400 transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <EyeOff className="w-5 h-5" />
                  ) : (
                    <Eye className="w-5 h-5" />
                  )}
                </button>
              </div>

              {/* Sign In Button */}
              <motion.button
                type="submit"
                whileHover={{ scale: isLoading ? 1 : 1.02 }}
                whileTap={{ scale: isLoading ? 1 : 0.98 }}
                disabled={isLoading}
                className="w-full h-14 bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 text-white rounded-xl transition-all duration-200 font-semibold shadow-lg hover:shadow-xl flex items-center justify-center gap-3 disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <span>Sign In</span>
                )}
              </motion.button>
            </motion.form>

            {/* Info */}
            <motion.p
              variants={itemVariants}
              className="text-center text-xs text-zinc-500 mt-6"
            >
              Admin access only
            </motion.p>
          </div>
        </motion.div>

        {/* Footer */}
        <motion.div
          variants={itemVariants}
          className="flex items-center justify-center gap-2 mt-6 text-zinc-600"
        >
          <Sparkles className="w-3.5 h-3.5 text-violet-500/60" />
          <span className="text-xs font-medium">Powered by RAG + Voice AI</span>
        </motion.div>
      </motion.div>
    </div>
  );
}
