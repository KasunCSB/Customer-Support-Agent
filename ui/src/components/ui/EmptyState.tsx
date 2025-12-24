/**
 * Empty State Component
 *
 * Placeholder for empty lists or states.
 *
 * @example
 * ```tsx
 * <EmptyState
 *   icon={<MessageSquare />}
 *   title="No messages"
 *   description="Start a conversation to see messages here."
 *   action={<Button>New Chat</Button>}
 * />
 * ```
 */

import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

const EmptyState = ({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) => {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-12 px-4 text-center',
        className
      )}
    >
      {icon && (
        <div className="mb-4 text-neutral-400 dark:text-neutral-600">
          <div className="w-12 h-12">{icon}</div>
        </div>
      )}
      <h3 className="text-lg font-medium text-neutral-900 dark:text-neutral-100 mb-1">
        {title}
      </h3>
      {description && (
        <p className="text-sm text-neutral-500 dark:text-neutral-400 max-w-sm mb-4">
          {description}
        </p>
      )}
      {action && <div>{action}</div>}
    </div>
  );
};

export { EmptyState };
