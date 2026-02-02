'use client';

import { Skeleton } from '@/components/ui/skeleton';

interface MessageSkeletonProps {
  variant?: 'text' | 'table' | 'chart' | 'full';
}

export function MessageSkeleton({ variant = 'text' }: MessageSkeletonProps) {
  return (
    <div className="flex w-full justify-start">
      <div className="max-w-[85%] md:max-w-[75%]">
        {/* Avatar and name skeleton */}
        <div className="flex items-center gap-3 mb-2">
          <Skeleton className="w-7 h-7 rounded-lg" />
          <Skeleton className="w-16 h-4 rounded" />
        </div>

        {/* Text skeleton (default) */}
        {variant === 'text' && (
          <div className="space-y-2 p-4 rounded-xl bg-card/50 border border-border">
            <Skeleton className="h-4 w-64 rounded" />
            <Skeleton className="h-4 w-48 rounded" />
            <Skeleton className="h-4 w-56 rounded" />
          </div>
        )}

        {/* Table skeleton */}
        {variant === 'table' && (
          <div className="space-y-2 p-4 rounded-xl bg-card/50 border border-border">
            <Skeleton className="h-4 w-48 rounded mb-3" />
            {/* Table header */}
            <div className="flex gap-2 mb-2">
              <Skeleton className="h-8 w-24 rounded" />
              <Skeleton className="h-8 w-32 rounded" />
              <Skeleton className="h-8 w-28 rounded" />
            </div>
            {/* Table rows */}
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex gap-2">
                <Skeleton className="h-6 w-24 rounded" />
                <Skeleton className="h-6 w-32 rounded" />
                <Skeleton className="h-6 w-28 rounded" />
              </div>
            ))}
          </div>
        )}

        {/* Chart skeleton */}
        {variant === 'chart' && (
          <div className="space-y-2 p-4 rounded-xl bg-card/50 border border-border">
            <Skeleton className="h-4 w-40 rounded mb-3" />
            {/* Chart area */}
            <div className="relative h-48 w-full">
              {/* Y-axis labels */}
              <div className="absolute left-0 top-0 h-full flex flex-col justify-between py-2">
                {[1, 2, 3, 4].map((i) => (
                  <Skeleton key={i} className="h-3 w-8 rounded" />
                ))}
              </div>
              {/* Bars */}
              <div className="absolute left-12 right-0 bottom-6 h-36 flex items-end gap-2">
                {[40, 65, 85, 50, 75, 90].map((h, i) => (
                  <Skeleton key={i} className="flex-1 rounded-t" style={{ height: `${h}%` }} />
                ))}
              </div>
              {/* X-axis labels */}
              <div className="absolute bottom-0 left-12 right-0 flex justify-between">
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <Skeleton key={i} className="h-3 w-8 rounded" />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Full skeleton (text + chart) */}
        {variant === 'full' && (
          <div className="space-y-3 p-4 rounded-xl bg-card/50 border border-border">
            {/* Text content */}
            <div className="space-y-2">
              <Skeleton className="h-4 w-64 rounded" />
              <Skeleton className="h-4 w-48 rounded" />
            </div>
            {/* Chart placeholder */}
            <div className="mt-3 pt-3 border-t border-border/50">
              <Skeleton className="h-4 w-32 rounded mb-2" />
              <div className="h-36 flex items-end gap-2">
                {[40, 65, 85, 50, 75].map((h, i) => (
                  <Skeleton key={i} className="flex-1 rounded-t" style={{ height: `${h}%` }} />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Export convenience components for specific use cases
export function TableSkeleton() {
  return <MessageSkeleton variant="table" />;
}

export function ChartSkeleton() {
  return <MessageSkeleton variant="chart" />;
}

export function FullMessageSkeleton() {
  return <MessageSkeleton variant="full" />;
}
