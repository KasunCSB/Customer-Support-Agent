/**
 * Mode Switcher Component
 *
 * A modern 3-way pill-style switch for selecting between Chat, Voice, and Conversation modes.
 * Features acrylic/glass effect and smooth animations.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { MessageSquare, Mic, Waves } from 'lucide-react';
import { CHAT_MODES, type ChatModeId } from '@/lib/config';

interface ModeSwitcherProps {
  value: ChatModeId;
  onChange: (mode: ChatModeId) => void;
  className?: string;
}

const icons = {
  MessageSquare,
  Mic,
  Waves,
};

const ModeSwitcher = memo(function ModeSwitcher({
  value,
  onChange,
  className,
}: ModeSwitcherProps) {
  const activeIndex = CHAT_MODES.findIndex((mode) => mode.id === value);

  return (
    <div className={cn('flex flex-col items-center gap-3 sm:gap-4', className)}>
      {/* Main pill container */}
      <div
        className={cn(
          'relative flex items-stretch gap-1 p-1.5',
          'bg-white/10 dark:bg-black/20',
          'backdrop-blur-xl',
          'border border-white/20 dark:border-white/10',
          'rounded-full',
          'shadow-lg shadow-black/5 dark:shadow-black/20'
        )}
      >
        {/* Active indicator - slides behind active option */}
        <div
          className={cn(
            'absolute top-1.5 bottom-1.5 rounded-full',
            'bg-white dark:bg-white/20',
            'shadow-md shadow-black/10',
            'transition-all duration-300 ease-out'
          )}
          style={{
            left: `calc(${activeIndex * 33.33}% + 6px)`,
            width: 'calc(33.33% - 4px)',
          }}
        />

        {/* Mode buttons */}
        {CHAT_MODES.map((mode) => {
          const Icon = icons[mode.icon];
          const isActive = value === mode.id;

          return (
            <button
              key={mode.id}
              onClick={() => onChange(mode.id)}
              className={cn(
                'relative z-10 flex items-center gap-2 px-4 py-2.5 sm:px-6 sm:py-3',
                'rounded-full transition-all duration-300',
                'font-medium text-sm',
                isActive
                  ? 'text-neutral-900 dark:text-white'
                  : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200'
              )}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden sm:inline">{mode.label}</span>
            </button>
          );
        })}
      </div>

      {/* Description text for active mode */}
      <p
        className={cn(
          'text-xs sm:text-sm text-center max-w-xs',
          'text-neutral-500 dark:text-neutral-400',
          'transition-opacity duration-300'
        )}
      >
        {CHAT_MODES.find((m) => m.id === value)?.description}
      </p>
    </div>
  );
});

export { ModeSwitcher };
