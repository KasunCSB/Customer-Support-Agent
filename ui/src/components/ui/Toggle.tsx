/**
 * Toggle/Switch Component
 *
 * A toggle switch for boolean values.
 *
 * @example
 * ```tsx
 * <Toggle
 *   label="Dark Mode"
 *   checked={isDark}
 *   onChange={setIsDark}
 * />
 * ```
 */

'use client';

import { useId } from 'react';
import { cn } from '@/lib/utils';

interface ToggleProps {
  label?: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
  size?: 'sm' | 'md';
}

const Toggle = ({
  label,
  description,
  checked,
  onChange,
  disabled = false,
  className,
  size = 'md',
}: ToggleProps) => {
  const id = useId();

  const sizeClasses = {
    sm: 'h-5 w-9',
    md: 'h-6 w-11',
  };

  const thumbSizeClasses = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
  };

  const thumbTranslateClasses = {
    sm: checked ? 'translate-x-5' : 'translate-x-1',
    md: checked ? 'translate-x-6' : 'translate-x-1',
  };

  return (
    <div className={cn('flex items-center justify-between', className)}>
      {(label || description) && (
        <div className="flex-1 mr-4">
          {label && (
            <label
              htmlFor={id}
              className={cn(
                'text-sm font-medium text-neutral-700 dark:text-neutral-300',
                disabled && 'opacity-50'
              )}
            >
              {label}
            </label>
          )}
          {description && (
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">
              {description}
            </p>
          )}
        </div>
      )}

      <button
        id={id}
        role="switch"
        type="button"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative inline-flex items-center rounded-full',
          'transition-colors duration-200 ease-in-out',
          'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          sizeClasses[size],
          checked
            ? 'bg-primary-600'
            : 'bg-neutral-200 dark:bg-neutral-700'
        )}
      >
        <span
          className={cn(
            'inline-block transform rounded-full bg-white',
            'shadow-sm transition-transform duration-200 ease-in-out',
            thumbSizeClasses[size],
            thumbTranslateClasses[size]
          )}
        />
      </button>
    </div>
  );
};

export { Toggle };
