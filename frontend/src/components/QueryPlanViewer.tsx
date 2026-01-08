'use client';

import { QueryPlan } from '@/lib/types';

interface QueryPlanViewerProps {
  plan: QueryPlan | null;
}

export function QueryPlanViewer({ plan }: QueryPlanViewerProps) {
  if (!plan) return null;

  // Safely stringify the plan to prevent any injection
  const safeJsonString = JSON.stringify(plan, null, 2);

  return (
    <div className="w-full max-h-[400px] overflow-y-auto custom-scrollbar">
      <div className="mb-2 text-xs font-semibold text-zinc-500 uppercase tracking-wider">
        Query Plan
      </div>
      <pre className="text-xs font-mono text-zinc-300 whitespace-pre-wrap break-words">
        {safeJsonString}
      </pre>
    </div>
  );
}
