'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Loader2, Sparkles, Database, MessageSquare, Mic } from 'lucide-react';
import { toast } from 'sonner';
import { getApiBaseUrl } from '@/lib/constants';

interface AuthScreenProps {
  onLogin: (username: string) => void;
}

export function AuthScreen({ onLogin }: AuthScreenProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleGoogleLogin = async () => {
    setIsLoading(true);

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/auth/google`);

      if (!response.ok) {
        throw new Error('Failed to initiate Google login');
      }

      const data = await response.json();
      const authUrl = data.url || data.auth_url;

      if (authUrl) {
        window.location.href = authUrl;
      } else {
        throw new Error('No auth URL received');
      }
    } catch (err) {
      console.error('Google login error:', err);
      setIsLoading(false);
      toast.error('Sign In Failed', {
        description: 'Unable to connect to Google. Please try again.',
      });
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
    <div className="min-h-screen w-full bg-background flex items-center justify-center p-4 relative overflow-hidden">
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

            {/* Google Sign In Button */}
            <motion.div variants={itemVariants}>
              <motion.button
                whileHover={{ scale: isLoading ? 1 : 1.02 }}
                whileTap={{ scale: isLoading ? 1 : 0.98 }}
                onClick={handleGoogleLogin}
                disabled={isLoading}
                className="w-full h-14 bg-white hover:bg-gray-50 text-gray-800 rounded-xl transition-all duration-200 font-semibold shadow-lg hover:shadow-xl flex items-center justify-center gap-3 disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin text-gray-600" />
                ) : (
                  <>
                    <svg className="w-5 h-5" viewBox="0 0 24 24">
                      <path
                        fill="#4285F4"
                        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                      />
                      <path
                        fill="#34A853"
                        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                      />
                      <path
                        fill="#FBBC05"
                        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                      />
                      <path
                        fill="#EA4335"
                        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                      />
                    </svg>
                    <span>Continue with Google</span>
                  </>
                )}
              </motion.button>
            </motion.div>

            {/* Terms */}
            <motion.p
              variants={itemVariants}
              className="text-center text-xs text-zinc-500 mt-6"
            >
              By signing in, you agree to connect your Google Sheets data
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
