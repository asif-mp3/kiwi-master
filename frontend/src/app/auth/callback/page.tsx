'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

export default function AuthCallbackPage() {
  const router = useRouter();

  useEffect(() => {
    // OAuth callback page is no longer used
    // Redirect to home page
    router.push('/');
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0F0A1A]">
      <Loader2 className="w-16 h-16 text-violet-500 animate-spin" />
    </div>
  );
}
