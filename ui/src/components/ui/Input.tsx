/**
 * Input Component
 *
 * A styled input component with label, error, and icon support.
 *
 * @example
 * ```tsx
 * <Input
 *   label="Email"
 *   placeholder="Enter your email"
 *   error="Invalid email address"
 * />
 * ```
 */

import { forwardRef, useId } from 'react';
import { cn } from '@/lib/utils';
import type { InputProps } from '@/types/components';

const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      label,
      error,
      hint,
      leftElement,
      rightElement,
      type = 'text',
      disabled,
      ...props
    },
    ref
  ) => {
    const id = useId();

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={id}
            className={cn(
              'block text-sm font-medium mb-1.5',
              'text-neutral-700 dark:text-neutral-300',
              disabled && 'opacity-50'
            )}
          >
            {label}
          </label>
        )}

        <div className="relative">
          {leftElement && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400">
              {leftElement}
            </div>
          )}

          <input
            ref={ref}
            id={id}
            type={type}
            disabled={disabled}
            className={cn(
              'w-full rounded-lg border bg-white px-4 py-2.5',
              'text-neutral-900 placeholder-neutral-400',
              'transition-all duration-200',
              'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
              'disabled:bg-neutral-100 disabled:cursor-not-allowed',
              'dark:bg-neutral-800 dark:text-neutral-100 dark:placeholder-neutral-500',
              error
                ? 'border-error-500 focus:ring-error-500'
                : 'border-neutral-300 dark:border-neutral-600',
              leftElement && 'pl-10',
              rightElement && 'pr-10',
              className
            )}
            {...props}
          />

          {rightElement && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400">
              {rightElement}
            </div>
          )}
        </div>

        {(error || hint) && (
          <p
            className={cn(
              'mt-1.5 text-sm',
              error ? 'text-error-600 dark:text-error-500' : 'text-neutral-500'
            )}
          >
            {error || hint}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export { Input };
