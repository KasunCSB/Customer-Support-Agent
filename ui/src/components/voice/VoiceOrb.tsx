/**
 * Voice Orb Component - Redesigned
 *
 * Uses the AnimatedOrb component with state-based animations
 * for listening, thinking, speaking, and idle states.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { AnimatedOrb, type OrbState } from '@/components/ui/AnimatedOrb';
import { MicOff } from 'lucide-react';

type VoiceOrbState = 'idle' | 'listening' | 'thinking' | 'speaking';

interface VoiceOrbProps {
  state: VoiceOrbState;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  onClick?: () => void;
  disabled?: boolean;
  isMuted?: boolean;
  isActive?: boolean;
  className?: string;
}

const VoiceOrb = memo(function VoiceOrb({
  state,
  size = 'lg',
  onClick,
  disabled = false,
  isMuted = false,
  isActive = false,
  className,
}: VoiceOrbProps) {
  // Map VoiceOrbState to AnimatedOrb state
  const orbState: OrbState = isMuted ? 'idle' : state;

  // Size mapping for the container
  const containerSizes = {
    sm: 'w-20 h-20',
    md: 'w-28 h-28',
    lg: 'w-40 h-40',
    xl: 'w-56 h-56',
  };

  // Map to AnimatedOrb sizes
  const orbSizes = {
    sm: 'sm' as const,
    md: 'md' as const,
    lg: 'lg' as const,
    xl: 'xl' as const,
  };

  return (
    <div
      className={cn(
        'relative flex items-center justify-center',
        containerSizes[size],
        className
      )}
    >
      {/* Main orb */}
      <AnimatedOrb
        state={orbState}
        size={orbSizes[size]}
        enableBreathing={!disabled && !isMuted}
        enableParticles={!disabled}
        onClick={onClick}
        className={cn(
          disabled && 'opacity-50 cursor-not-allowed',
          'w-full h-full'
        )}
      />

      {/* Muted overlay */}
      {isMuted && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="p-4 rounded-full bg-neutral-900/60 backdrop-blur-sm">
            <MicOff className="w-8 h-8 text-white" />
          </div>
        </div>
      )}

      {/* Call status indicator */}
      {isActive && (
        <div
          className={cn(
            'absolute -bottom-2 left-1/2 -translate-x-1/2',
            'flex items-center gap-2 px-4 py-2 rounded-full',
            'bg-white/80 dark:bg-neutral-800/80',
            'backdrop-blur-xl',
            'border border-white/30 dark:border-white/10',
            'shadow-lg',
            'animate-slide-up'
          )}
        >
          <span
            className={cn(
              'w-2 h-2 rounded-full',
              state === 'idle' ? 'bg-neutral-400' : 'bg-green-500 animate-pulse'
            )}
          />
          <span className="text-xs font-medium text-neutral-700 dark:text-neutral-300">
            {state === 'listening' && 'Listening...'}
            {state === 'thinking' && 'Processing...'}
            {state === 'speaking' && 'Speaking...'}
            {state === 'idle' && 'Ready'}
          </span>
        </div>
      )}
    </div>
  );
});

export { VoiceOrb };
export type { VoiceOrbState };
