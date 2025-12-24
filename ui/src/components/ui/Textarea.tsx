/**
 * Textarea Component
 *
 * A styled textarea with auto-resize support.
 *
 * @example
 * ```tsx
 * <Textarea
 *   label="Message"
 *   placeholder="Type your message..."
 *   autoResize
 * />
 * ```
 */

import { forwardRef, useId, useRef, useEffect, TextareaHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
  autoResize?: boolean;
  maxRows?: number;
}

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      className,
      label,
      error,
      hint,
      autoResize = false,
      maxRows = 10,
      rows = 3,
      disabled,
      ...props
    },
    ref
  ) => {
    const id = useId();
    const internalRef = useRef<HTMLTextAreaElement>(null);
    const textareaRef = (ref as React.RefObject<HTMLTextAreaElement>) || internalRef;

    useEffect(() => {
      if (!autoResize || !textareaRef.current) return;

      const textarea = textareaRef.current;
      const adjustHeight = () => {
        textarea.style.height = 'auto';
        const lineHeight = parseInt(getComputedStyle(textarea).lineHeight);
        const maxHeight = lineHeight * maxRows;
        const newHeight = Math.min(textarea.scrollHeight, maxHeight);
        textarea.style.height = `${newHeight}px`;
      };

      adjustHeight();
      textarea.addEventListener('input', adjustHeight);
      return () => textarea.removeEventListener('input', adjustHeight);
    }, [autoResize, maxRows, textareaRef]);

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

        <textarea
          ref={textareaRef}
          id={id}
          rows={rows}
          disabled={disabled}
          className={cn(
            'w-full rounded-lg border bg-white px-4 py-3',
            'text-neutral-900 placeholder-neutral-400',
            'transition-all duration-200 resize-none',
            'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
            'disabled:bg-neutral-100 disabled:cursor-not-allowed',
            'dark:bg-neutral-800 dark:text-neutral-100 dark:placeholder-neutral-500',
            error
              ? 'border-error-500 focus:ring-error-500'
              : 'border-neutral-300 dark:border-neutral-600',
            className
          )}
          {...props}
        />

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

Textarea.displayName = 'Textarea';

export { Textarea };
