'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { Loader2, CheckCircle2, XCircle, FileSpreadsheet } from 'lucide-react';
import { api } from '@/services/api';

export default function SheetsCallbackPage() {
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
        setError('Google Sheets authorization was cancelled or failed.');
        return;
      }

      if (!code) {
        setStatus('error');
        setError('No authorization code received.');
        return;
      }

      try {
        // Exchange the code for tokens
        const result = await api.exchangeSheetsCode(code);

        if (result.success) {
          setStatus('success');

          // Redirect back to main app after a short delay
          setTimeout(() => {
            router.push('/');
          }, 1500);
        } else {
          throw new Error('Failed to authorize Google Sheets');
        }

      } catch (err) {
        console.error('Sheets callback error:', err);
        setStatus('error');
        setError(err instanceof Error ? err.message : 'Failed to authorize Google Sheets');
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
            <div className="relative">
              <FileSpreadsheet className="w-16 h-16 text-green-500 mx-auto opacity-50" />
              <Loader2 className="w-8 h-8 text-violet-500 animate-spin absolute bottom-0 right-1/2 translate-x-1/2 translate-y-2" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white mb-2">Connecting Google Sheets...</h2>
              <p className="text-zinc-400">Please wait while we authorize access.</p>
            </div>
          </>
        )}

        {status === 'success' && (
          <>
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', damping: 15 }}
              className="relative"
            >
              <FileSpreadsheet className="w-16 h-16 text-green-500 mx-auto" />
              <CheckCircle2 className="w-6 h-6 text-green-400 absolute bottom-0 right-1/2 translate-x-4 translate-y-1" />
            </motion.div>
            <div>
              <h2 className="text-2xl font-bold text-white mb-2">Google Sheets Connected!</h2>
              <p className="text-zinc-400">You can now access your Google Sheets data.</p>
              <p className="text-zinc-500 text-sm mt-2">Redirecting you back to the app...</p>
            </div>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle className="w-16 h-16 text-red-500 mx-auto" />
            <div>
              <h2 className="text-2xl font-bold text-white mb-2">Authorization Failed</h2>
              <p className="text-zinc-400 mb-4">{error}</p>
              <button
                onClick={() => router.push('/')}
                className="px-6 py-3 bg-violet-600 hover:bg-violet-500 text-white rounded-xl font-medium transition-colors"
              >
                Back to App
              </button>
            </div>
          </>
        )}
      </motion.div>
    </div>
  );
}
