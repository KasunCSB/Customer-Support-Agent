/**
 * Card Component
 *
 * A container component with various visual styles.
 *
 * @example
 * ```tsx
 * <Card variant="elevated" padding="md">
 *   <CardHeader>Title</CardHeader>
 *   <CardContent>Content</CardContent>
 * </Card>
 * ```
 */

import { forwardRef, HTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/utils';
import type { CardProps, Size } from '@/types/components';

const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      className,
      children,
      variant = 'elevated',
      padding = 'md',
      hoverable = false,
      ...props
    },
    ref
  ) => {
    const variants = {
      elevated: cn(
        'bg-white shadow-soft',
        'dark:bg-neutral-900 dark:shadow-none dark:border dark:border-neutral-800'
      ),
      outlined: cn(
        'bg-white border border-neutral-200',
        'dark:bg-neutral-900 dark:border-neutral-800'
      ),
      flat: cn('bg-neutral-50', 'dark:bg-neutral-900'),
    };

    const paddings: Record<Size | 'none', string> = {
      none: '',
      sm: 'p-3',
      md: 'p-4',
      lg: 'p-6',
      xl: 'p-8',
    };

    return (
      <div
        ref={ref}
        className={cn(
          'rounded-xl',
          variants[variant],
          paddings[padding],
          hoverable && 'transition-all duration-200 hover:shadow-soft-lg hover:-translate-y-0.5',
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  action?: ReactNode;
}

const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, children, action, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex items-center justify-between mb-4', className)}
      {...props}
    >
      <div className="font-semibold text-lg text-neutral-900 dark:text-neutral-100">
        {children}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
);

CardHeader.displayName = 'CardHeader';

const CardContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('text-neutral-600 dark:text-neutral-400', className)}
      {...props}
    >
      {children}
    </div>
  )
);

CardContent.displayName = 'CardContent';

const CardFooter = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'flex items-center justify-end gap-2 mt-4 pt-4',
        'border-t border-neutral-200 dark:border-neutral-800',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
);

CardFooter.displayName = 'CardFooter';

export { Card, CardHeader, CardContent, CardFooter };
