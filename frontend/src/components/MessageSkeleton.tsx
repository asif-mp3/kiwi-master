'use client';

import { Skeleton } from '@/components/ui/skeleton';

export function MessageSkeleton() {
  return (
    <div className="flex w-full justify-start">
      <div className="max-w-[75%]">
        {/* Avatar and name skeleton */}
        <div className="flex items-center gap-3 mb-2">
          <Skeleton className="w-7 h-7 rounded-lg" />
          <Skeleton className="w-16 h-4 rounded" />
        </div>
        {/* Message bubble skeleton */}
        <div className="space-y-2">
          <Skeleton className="h-4 w-64 rounded" />
          <Skeleton className="h-4 w-48 rounded" />
          <Skeleton className="h-4 w-56 rounded" />
        </div>
      </div>
    </div>
  );
}
