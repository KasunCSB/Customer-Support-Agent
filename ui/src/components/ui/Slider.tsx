/**
 * Slider Component
 *
 * A range slider for numeric value selection.
 *
 * @example
 * ```tsx
 * <Slider
 *   label="Temperature"
 *   value={0.7}
 *   min={0}
 *   max={2}
 *   step={0.1}
 *   onChange={setValue}
 * />
 * ```
 */

'use client';

import { useId } from 'react';
import { cn } from '@/lib/utils';

interface SliderProps {
  label?: string;
  description?: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
  formatValue?: (value: number) => string;
  className?: string;
  disabled?: boolean;
}

const Slider = ({
  label,
  description,
  value,
  min,
  max,
  step = 1,
  onChange,
  formatValue,
  className,
  disabled = false,
}: SliderProps) => {
  const id = useId();
  const displayValue = formatValue ? formatValue(value) : value.toString();

  // Calculate percentage for gradient
  const percentage = ((value - min) / (max - min)) * 100;

  return (
    <div className={cn('w-full', className)}>
      <div className="flex items-center justify-between mb-2">
        {label && (
          <div className="flex-1">
            <label
              htmlFor={id}
              className={cn(
                'block text-sm font-medium',
                'text-neutral-700 dark:text-neutral-300',
                disabled && 'opacity-50'
              )}
            >
              {label}
            </label>
            {description && (
              <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
                {description}
              </p>
            )}
          </div>
        )}
        <span className={cn(
          'text-sm font-medium text-neutral-900 dark:text-neutral-100',
          disabled && 'opacity-50',
          !label && 'ml-auto'
        )}>
          {displayValue}
        </span>
      </div>

      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        disabled={disabled}
        className={cn(
          'w-full h-2 rounded-full appearance-none cursor-pointer',
          'bg-neutral-200 dark:bg-neutral-700',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          // Custom styling for the track
          '[&::-webkit-slider-thumb]:appearance-none',
          '[&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4',
          '[&::-webkit-slider-thumb]:rounded-full',
          '[&::-webkit-slider-thumb]:bg-primary-600',
          '[&::-webkit-slider-thumb]:shadow-md',
          '[&::-webkit-slider-thumb]:transition-transform',
          '[&::-webkit-slider-thumb]:hover:scale-110',
          '[&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4',
          '[&::-moz-range-thumb]:rounded-full',
          '[&::-moz-range-thumb]:bg-primary-600',
          '[&::-moz-range-thumb]:border-0',
          '[&::-moz-range-thumb]:shadow-md'
        )}
        style={{
          background: `linear-gradient(to right, #2563eb 0%, #2563eb ${percentage}%, #e5e5e5 ${percentage}%, #e5e5e5 100%)`,
        }}
      />

      <div className="flex justify-between mt-1">
        <span className="text-xs text-neutral-400">{min}</span>
        <span className="text-xs text-neutral-400">{max}</span>
      </div>
    </div>
  );
};

export { Slider };
