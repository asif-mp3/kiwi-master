'use client';

interface QueryPlanViewerProps {
  plan: any;
}

export function QueryPlanViewer({ plan }: QueryPlanViewerProps) {
  if (!plan) return null;

  return (
    <div className="w-full max-h-[400px] overflow-y-auto custom-scrollbar">
      <pre className="text-xs font-mono text-zinc-300 whitespace-pre-wrap">
        {JSON.stringify(plan, null, 2)}
      </pre>
    </div>
  );
}
