'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { api } from '@/services/api';

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const errorParam = searchParams.get('error');

      if (errorParam) {
        setStatus('error');
        setError('Authentication was cancelled or failed.');
        return;
      }

      if (!code) {
        setStatus('error');
        setError('No authorization code received.');
        return;
      }

      try {
        // Exchange the code for tokens using centralized API service
        const data = await api.authCallback(code);

        // Store the access token
        if (data.access_token) {
          localStorage.setItem('thara_access_token', data.access_token);
          localStorage.setItem('thara_auth', JSON.stringify({
            isAuthenticated: true,
            username: data.user?.name || data.user?.email || 'User',
            user: data.user
          }));
        }

        setStatus('success');

        // Redirect to main app after a short delay
        setTimeout(() => {
          router.push('/');
        }, 1500);

      } catch (err) {
        console.error('Auth callback error:', err);
        setStatus('error');
        setError(err instanceof Error ? err.message : 'Authentication failed');
      }
    };

    handleCallback();
  }, [searchParams, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0F0A1A]">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="text-center space-y-6"
      >
        {status === 'processing' && (
          <>
            <Loader2 className="w-16 h-16 text-violet-500 animate-spin mx-auto" />
            <div>
              <h2 className="text-2xl font-bold text-white mb-2">Authenticating...</h2>
              <p className="text-zinc-400">Please wait while we complete your sign in.</p>
            </div>
          </>
        )}

        {status === 'success' && (
          <>
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', damping: 15 }}
            >
              <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto" />
            </motion.div>
            <div>
              <h2 className="text-2xl font-bold text-white mb-2">Welcome to Thara.ai!</h2>
              <p className="text-zinc-400">Redirecting you to the app...</p>
            </div>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle className="w-16 h-16 text-red-500 mx-auto" />
            <div>
              <h2 className="text-2xl font-bold text-white mb-2">Authentication Failed</h2>
              <p className="text-zinc-400 mb-4">{error}</p>
              <button
                onClick={() => router.push('/')}
                className="px-6 py-3 bg-violet-600 hover:bg-violet-500 text-white rounded-xl font-medium transition-colors"
              >
                Back to Login
              </button>
            </div>
          </>
        )}
      </motion.div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-[#0F0A1A]">
        <Loader2 className="w-16 h-16 text-violet-500 animate-spin" />
      </div>
    }>
      <AuthCallbackContent />
    </Suspense>
  );
}
