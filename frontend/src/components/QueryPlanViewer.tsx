'use client';

import { useState } from 'react';
import { QueryPlan } from '@/lib/types';

interface QueryPlanViewerProps {
  plan: QueryPlan | null;
}

export function QueryPlanViewer({ plan }: QueryPlanViewerProps) {
  const [copied, setCopied] = useState(false);

  if (!plan) return null;

  // Safely stringify the plan to prevent any injection
  const safeJsonString = JSON.stringify(plan, null, 2);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(safeJsonString);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="w-full max-h-[400px] overflow-y-auto custom-scrollbar">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
          Query Plan
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-1 text-xs text-zinc-400 hover:text-zinc-200 bg-zinc-800 hover:bg-zinc-700 rounded transition-colors"
          title="Copy to clipboard"
        >
          {copied ? (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              <span>Copied!</span>
            </>
          ) : (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
                <path d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z" />
              </svg>
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="text-xs font-mono text-zinc-300 whitespace-pre-wrap break-words">
        {safeJsonString}
      </pre>
    </div>
  );
}
