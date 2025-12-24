/**
 * Voice Controls Component
 *
 * Modern floating controls for voice chat with mode toggle and stop button.
 */

'use client';

import { cn } from '@/lib/utils';
import { Mic, Square, Waves } from 'lucide-react';

interface VoiceControlsProps {
  isListening: boolean;
  isActive: boolean;
  mode: 'push-to-talk' | 'continuous';
  onModeChange: (mode: 'push-to-talk' | 'continuous') => void;
  onStop: () => void;
  className?: string;
}

const VoiceControls = ({
  isListening,
  isActive,
  mode,
  onModeChange,
  onStop,
  className,
}: VoiceControlsProps) => {
  return (
    <div
      className={cn(
        'flex items-center justify-center gap-4 p-4',
        className
      )}
    >
      {/* Floating control bar */}
      <div
        className={cn(
          'flex items-center gap-3 px-6 py-3',
          'rounded-full',
          'bg-white/70 dark:bg-neutral-900/70',
          'backdrop-blur-xl',
          'border border-white/30 dark:border-white/10',
          'shadow-2xl shadow-black/10 dark:shadow-black/30'
        )}
      >
        {/* Mode toggle pills */}
        <div className="flex items-center gap-1 p-1 rounded-full bg-neutral-100/50 dark:bg-neutral-800/50">
          <button
            onClick={() => onModeChange('push-to-talk')}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-full',
              'text-sm font-medium transition-all duration-300',
              mode === 'push-to-talk'
                ? 'bg-white dark:bg-white/20 shadow-md text-neutral-900 dark:text-white'
                : 'text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300'
            )}
          >
            <Mic className="w-4 h-4" />
            <span className="hidden sm:inline">Voice Chat</span>
          </button>
          <button
            onClick={() => onModeChange('continuous')}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-full',
              'text-sm font-medium transition-all duration-300',
              mode === 'continuous'
                ? 'bg-white dark:bg-white/20 shadow-md text-neutral-900 dark:text-white'
                : 'text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300'
            )}
          >
            <Waves className="w-4 h-4" />
            <span className="hidden sm:inline">Realtime</span>
          </button>
        </div>

        {/* Divider */}
        <div className="w-px h-8 bg-neutral-200/50 dark:bg-neutral-700/50" />

        {/* Status indicator */}
        <div className="flex items-center gap-2">
          <div
            className={cn(
              'w-2.5 h-2.5 rounded-full transition-colors duration-300',
              isActive
                ? isListening
                  ? 'bg-green-500 animate-pulse'
                  : 'bg-blue-500 animate-pulse'
                : 'bg-neutral-400'
            )}
          />
          <span className="text-sm text-neutral-600 dark:text-neutral-400">
            {isActive ? (isListening ? 'Listening' : 'Active') : 'Ready'}
          </span>
        </div>

        {/* Divider - only show when active */}
        {isActive && (
          <>
            <div className="w-px h-8 bg-neutral-200/50 dark:bg-neutral-700/50" />

            {/* Stop button */}
            <button
              onClick={onStop}
              className={cn(
                'p-3 rounded-full',
                'bg-red-500 text-white',
                'hover:bg-red-600',
                'transition-all duration-300',
                'shadow-lg shadow-red-500/30'
              )}
              aria-label="Stop"
            >
              <Square className="w-5 h-5 fill-current" />
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export { VoiceControls };
