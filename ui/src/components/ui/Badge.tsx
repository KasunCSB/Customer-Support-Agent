/**
 * Badge Component
 *
 * Small status indicators and labels.
 *
 * @example
 * ```tsx
 * <Badge variant="success">Active</Badge>
 * <Badge variant="warning" size="sm">Pending</Badge>
 * ```
 */

import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

type BadgeVariant = 'default' | 'primary' | 'secondary' | 'success' | 'warning' | 'error';
type BadgeSize = 'sm' | 'md';

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  className?: string;
}

const Badge = ({
  children,
  variant = 'default',
  size = 'md',
  className,
}: BadgeProps) => {
  const variants: Record<BadgeVariant, string> = {
    default: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
    primary: 'bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300',
    secondary: 'bg-secondary-100 text-secondary-700 dark:bg-secondary-900 dark:text-secondary-300',
    success: 'bg-success-100 text-success-700 dark:bg-success-700/20 dark:text-success-500',
    warning: 'bg-warning-100 text-warning-700 dark:bg-warning-700/20 dark:text-warning-500',
    error: 'bg-error-100 text-error-700 dark:bg-error-700/20 dark:text-error-500',
  };

  const sizes: Record<BadgeSize, string> = {
    sm: 'px-1.5 py-0.5 text-2xs',
    md: 'px-2 py-0.5 text-xs',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center font-medium rounded-full',
        variants[variant],
        sizes[size],
        className
      )}
    >
      {children}
    </span>
  );
};

export { Badge };
