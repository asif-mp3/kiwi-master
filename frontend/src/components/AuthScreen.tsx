'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Loader2, User, Lock, Eye, EyeOff } from 'lucide-react';
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

  return (
    <div className="min-h-[100dvh] w-full bg-gradient-to-br from-zinc-950 via-zinc-900 to-zinc-950 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="w-full max-w-sm"
      >
        {/* Card */}
        <div className="bg-zinc-900 rounded-2xl border border-zinc-800 shadow-xl overflow-hidden">
          <div className="p-6 sm:p-8">
            {/* Logo */}
            <div className="flex justify-center mb-6">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg">
                <span className="text-2xl font-bold text-white">T</span>
              </div>
            </div>

            {/* Title */}
            <div className="text-center mb-8">
              <h1 className="text-2xl sm:text-3xl font-semibold text-white mb-2">
                Welcome to{' '}
                <span className="text-violet-400">Thara.ai</span>
              </h1>
              <p className="text-zinc-400 text-sm">
                Your AI-powered analytics assistant
              </p>
            </div>

            {/* Login Form */}
            <form onSubmit={handleLogin} className="space-y-4">
              {/* User ID Input */}
              <div>
                <label htmlFor="userId" className="block text-sm font-medium text-zinc-400 mb-1.5">
                  User ID
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <User className="w-4 h-4 text-zinc-500" />
                  </div>
                  <input
                    id="userId"
                    type="text"
                    value={userId}
                    onChange={(e) => setUserId(e.target.value)}
                    placeholder="Enter your user ID"
                    disabled={isLoading}
                    autoComplete="username"
                    className="w-full h-11 pl-10 pr-4 bg-zinc-800/50 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500 transition-colors disabled:opacity-50"
                  />
                </div>
              </div>

              {/* Password Input */}
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-zinc-400 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="w-4 h-4 text-zinc-500" />
                  </div>
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    disabled={isLoading}
                    autoComplete="current-password"
                    className="w-full h-11 pl-10 pr-11 bg-zinc-800/50 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500 transition-colors disabled:opacity-50"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-zinc-500 hover:text-zinc-300 transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              {/* Sign In Button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full h-11 mt-2 bg-violet-600 hover:bg-violet-500 active:bg-violet-700 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Signing in...</span>
                  </>
                ) : (
                  <span>Sign In</span>
                )}
              </button>
            </form>

            {/* Footer */}
            <p className="text-center text-xs text-zinc-500 mt-6">
              Admin access only
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
