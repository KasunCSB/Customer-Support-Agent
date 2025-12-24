/**
 * Button Component
 *
 * A versatile button component with multiple variants and sizes.
 * Features floating, pill-style design with acrylic effects.
 *
 * @example
 * ```tsx
 * <Button variant="primary" size="md" onClick={handleClick}>
 *   Click me
 * </Button>
 * ```
 */

import { forwardRef } from 'react';
import { cn } from '@/lib/utils';
import type { ButtonProps } from '@/types/components';
import { Loader2 } from 'lucide-react';

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      children,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      pill = false,
      floating = false,
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles = cn(
      'inline-flex items-center justify-center gap-2',
      'font-medium transition-all duration-300',
      'focus:outline-none focus:ring-2 focus:ring-offset-2',
      'disabled:opacity-50 disabled:cursor-not-allowed',
      'active:scale-[0.97]',
      'hover:scale-[1.02]'
    );

    const variants = {
      primary: cn(
        'bg-gradient-to-r from-primary-500 to-primary-600 text-white',
        'hover:from-primary-600 hover:to-primary-700',
        'focus:ring-primary-500/50',
        'shadow-lg shadow-primary-500/20 hover:shadow-xl hover:shadow-primary-500/30',
        'dark:from-primary-500 dark:to-primary-600'
      ),
      secondary: cn(
        'bg-gradient-to-r from-secondary-500 to-secondary-600 text-white',
        'hover:from-secondary-600 hover:to-secondary-700',
        'focus:ring-secondary-500/50',
        'shadow-lg shadow-secondary-500/20 hover:shadow-xl hover:shadow-secondary-500/30'
      ),
      ghost: cn(
        'bg-white/50 dark:bg-neutral-800/50 text-neutral-700 dark:text-neutral-300',
        'backdrop-blur-sm',
        'hover:bg-white/80 dark:hover:bg-neutral-700/80',
        'focus:ring-neutral-400/50',
        'border border-white/20 dark:border-white/10'
      ),
      outline: cn(
        'bg-transparent text-neutral-700 dark:text-neutral-300',
        'border-2 border-neutral-300 dark:border-neutral-600',
        'hover:bg-neutral-100/50 dark:hover:bg-neutral-800/50',
        'hover:border-primary-400 dark:hover:border-primary-500',
        'focus:ring-neutral-400/50'
      ),
      danger: cn(
        'bg-gradient-to-r from-error-500 to-error-600 text-white',
        'hover:from-error-600 hover:to-error-700',
        'focus:ring-error-500/50',
        'shadow-lg shadow-error-500/20 hover:shadow-xl hover:shadow-error-500/30'
      ),
      accent: cn(
        'bg-gradient-to-r from-accent-500 to-accent-600 text-white',
        'hover:from-accent-600 hover:to-accent-700',
        'focus:ring-accent-500/50',
        'shadow-lg shadow-accent-500/20 hover:shadow-xl hover:shadow-accent-500/30'
      ),
    };

    const sizes = {
      sm: pill ? 'px-4 py-1.5 text-sm rounded-full' : 'px-3 py-1.5 text-sm rounded-xl',
      md: pill ? 'px-6 py-2.5 text-sm rounded-full' : 'px-4 py-2 text-sm rounded-xl',
      lg: pill ? 'px-8 py-3 text-base rounded-full' : 'px-5 py-2.5 text-base rounded-xl',
      xl: pill ? 'px-10 py-4 text-lg rounded-full' : 'px-6 py-3 text-lg rounded-2xl',
    };

    const floatingStyles = floating
      ? cn(
          'backdrop-blur-xl',
          'border border-white/20 dark:border-white/10',
          'shadow-2xl shadow-black/10 dark:shadow-black/30'
        )
      : '';

    return (
      <button
        ref={ref}
        className={cn(
          baseStyles,
          variants[variant],
          sizes[size],
          floatingStyles,
          fullWidth && 'w-full',
          className
        )}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          leftIcon
        )}
        {children}
        {!isLoading && rightIcon}
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button };
