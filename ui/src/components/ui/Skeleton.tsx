/**
 * Skeleton Loading Component
 *
 * Placeholder loading states for content.
 *
 * @example
 * ```tsx
 * <Skeleton className="h-4 w-full" />
 * <Skeleton variant="circular" className="h-10 w-10" />
 * ```
 */

import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
  variant?: 'rectangular' | 'circular' | 'text';
}

const Skeleton = ({ className, variant = 'rectangular' }: SkeletonProps) => {
  return (
    <div
      className={cn(
        'animate-pulse bg-neutral-200 dark:bg-neutral-800',
        variant === 'circular' && 'rounded-full',
        variant === 'rectangular' && 'rounded-lg',
        variant === 'text' && 'rounded h-4',
        className
      )}
    />
  );
};

/**
 * Chat message skeleton
 */
const ChatMessageSkeleton = ({ isUser = false }: { isUser?: boolean }) => {
  return (
    <div className={cn('flex gap-3', isUser && 'flex-row-reverse')}>
      <Skeleton variant="circular" className="h-8 w-8 flex-shrink-0" />
      <div className={cn('flex flex-col gap-2', isUser ? 'items-end' : 'items-start')}>
        <Skeleton className="h-4 w-24" />
        <Skeleton className={cn('h-16 w-64', isUser ? 'rounded-l-xl' : 'rounded-r-xl')} />
      </div>
    </div>
  );
};

/**
 * Session list item skeleton
 */
const SessionListSkeleton = () => {
  return (
    <div className="p-3 space-y-2">
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-3 w-1/2" />
    </div>
  );
};

/**
 * Card skeleton
 */
const CardSkeleton = () => {
  return (
    <div className="p-6 space-y-4 rounded-xl border border-neutral-200 dark:border-neutral-800">
      <Skeleton className="h-6 w-1/3" />
      <div className="space-y-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-4/5" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </div>
  );
};

export { Skeleton, ChatMessageSkeleton, SessionListSkeleton, CardSkeleton };
