/**
 * AnimatedOrb Component
 *
 * A vibrant, animated orb with:
 * - SVG noise texture for organic feel
 * - State-based color palettes with SMOOTH transitions
 * - Multiple animated gradient layers
 * - Emotion-based intensity modifiers
 */

'use client';

import { memo, useMemo, useId, type CSSProperties } from 'react';
import { cn } from '@/lib/utils';

export type OrbState = 'idle' | 'listening' | 'thinking' | 'speaking';
export type OrbEmotion = 'neutral' | 'happy' | 'curious' | 'focused';

interface AnimatedOrbProps {
  state?: OrbState;
  emotion?: OrbEmotion;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'hero';
  enableBreathing?: boolean;
  enableParticles?: boolean;
  onClick?: () => void;
  className?: string;
}

// State-based color palettes - vibrant and distinct
const STATE_PALETTES = {
  idle: {
    // Balanced purple/pink/cyan - calm and inviting
    base: ['#E879F9', '#A855F7', '#6366F1', '#3B82F6', '#06B6D4'],
    accent1: ['#F0ABFC', '#C084FC', '#818CF8'],
    accent2: ['#67E8F9', '#22D3EE', '#2DD4BF'],
    glow: 'from-purple-500/50 via-pink-500/40 to-cyan-400/40',
  },
  listening: {
    // Cyan/teal focused - less green, more balanced
    base: ['#22D3EE', '#06B6D4', '#0891B2', '#0E7490', '#155E75'],
    accent1: ['#67E8F9', '#22D3EE', '#06B6D4'],
    accent2: ['#A5F3FC', '#67E8F9', '#22D3EE'],
    glow: 'from-cyan-400/60 via-cyan-500/50 to-teal-500/45',
  },
  thinking: {
    // Deep purple/indigo/violet - contemplative
    base: ['#8B5CF6', '#7C3AED', '#6D28D9', '#4F46E5', '#4338CA'],
    accent1: ['#C4B5FD', '#A78BFA', '#818CF8'],
    accent2: ['#E879F9', '#D946EF', '#A855F7'],
    glow: 'from-violet-500/55 via-purple-600/50 to-indigo-500/45',
  },
  speaking: {
    // Warm orange/gold/coral - energetic and expressive
    base: ['#FB923C', '#F97316', '#EA580C', '#F59E0B', '#FBBF24'],
    accent1: ['#FDBA74', '#FCD34D', '#FDE047'],
    accent2: ['#FB7185', '#F472B6', '#E879F9'],
    glow: 'from-orange-500/60 via-amber-500/50 to-rose-400/50',
  },
};

const STATES: OrbState[] = ['idle', 'listening', 'thinking', 'speaking'];

// Single state layer component for clean rendering
const StateLayer = memo(function StateLayer({
  orbId,
  stateName,
  palette,
  isActive,
}: {
  orbId: string;
  stateName: string;
  palette: typeof STATE_PALETTES.idle;
  isActive: boolean;
}) {
  const layerId = `${orbId}-${stateName}`;
  
  return (
    <g
      className="transition-opacity duration-[5000ms] ease-in-out"
      style={{ opacity: isActive ? 1 : 0 }}
    >
      <defs>
        {/* Base gradient - state specific */}
        <radialGradient id={`${layerId}-base`} cx="30%" cy="25%" r="90%">
          <stop offset="0%" stopColor={palette.base[0]} />
          <stop offset="25%" stopColor={palette.base[1]} />
          <stop offset="50%" stopColor={palette.base[2]} />
          <stop offset="75%" stopColor={palette.base[3]} />
          <stop offset="100%" stopColor={palette.base[4]} />
        </radialGradient>

        {/* Accent layer 1 */}
        <radialGradient id={`${layerId}-accent1`} cx="70%" cy="30%" r="75%">
          <stop offset="0%" stopColor={palette.accent1[0]} stopOpacity="0.95" />
          <stop offset="45%" stopColor={palette.accent1[1]} stopOpacity="0.7" />
          <stop offset="100%" stopColor={palette.accent1[2]} stopOpacity="0" />
        </radialGradient>

        {/* Accent layer 2 */}
        <radialGradient id={`${layerId}-accent2`} cx="25%" cy="70%" r="70%">
          <stop offset="0%" stopColor={palette.accent2[0]} stopOpacity="0.9" />
          <stop offset="40%" stopColor={palette.accent2[1]} stopOpacity="0.65" />
          <stop offset="100%" stopColor={palette.accent2[2]} stopOpacity="0" />
        </radialGradient>

        {/* Core glow */}
        <radialGradient id={`${layerId}-core`} cx="45%" cy="40%" r="50%">
          <stop offset="0%" stopColor="white" stopOpacity="0.4" />
          <stop offset="30%" stopColor={palette.accent1[0]} stopOpacity="0.5" />
          <stop offset="100%" stopColor={palette.base[2]} stopOpacity="0" />
        </radialGradient>

        {/* Edge glow */}
        <radialGradient id={`${layerId}-edge`} cx="80%" cy="75%" r="65%">
          <stop offset="0%" stopColor={palette.accent2[0]} stopOpacity="0.8" />
          <stop offset="50%" stopColor={palette.accent2[1]} stopOpacity="0.4" />
          <stop offset="100%" stopColor="transparent" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Base layer */}
      <rect width="100" height="100" fill={`url(#${layerId}-base)`} />

      {/* Animated gradient layers */}
      <g className="orb-grad-layer orb-grad-1" style={{ mixBlendMode: 'screen' }}>
        <circle cx="50" cy="50" r="60" fill={`url(#${layerId}-accent1)`} opacity="0.9" />
      </g>

      <g className="orb-grad-layer orb-grad-2" style={{ mixBlendMode: 'screen' }}>
        <circle cx="50" cy="50" r="62" fill={`url(#${layerId}-accent2)`} opacity="0.85" />
      </g>

      <g className="orb-grad-layer orb-grad-3" style={{ mixBlendMode: 'overlay' }}>
        <circle cx="50" cy="50" r="55" fill={`url(#${layerId}-core)`} opacity="0.8" />
      </g>

      <g className="orb-grad-layer orb-grad-4" style={{ mixBlendMode: 'soft-light' }}>
        <circle cx="50" cy="50" r="58" fill={`url(#${layerId}-edge)`} opacity="0.7" />
      </g>
    </g>
  );
});

const AnimatedOrb = memo(function AnimatedOrb({
  state = 'idle',
  emotion = 'neutral',
  size = 'lg',
  enableBreathing = true,
  enableParticles: _enableParticles = true,
  onClick,
  className,
}: AnimatedOrbProps) {
  const sizes = {
    sm: { container: 'w-16 h-16' },
    md: { container: 'w-24 h-24' },
    lg: { container: 'w-32 h-32' },
    xl: { container: 'w-48 h-48' },
    hero: { container: 'w-64 h-64 md:w-80 md:h-80' },
  };

  // State-based animation classes
  const stateAnimations = useMemo(() => {
    switch (state) {
      case 'listening':
        return 'animate-orb-listening';
      case 'thinking':
        return 'animate-orb-thinking';
      case 'speaking':
        return 'animate-orb-speaking';
      default:
        return enableBreathing ? 'animate-orb-breathing' : '';
    }
  }, [state, enableBreathing]);

  // Animation speed based on state
  const waveSpeed = useMemo(() => {
    switch (state) {
      case 'listening':
        return 1.5;
      case 'thinking':
        return 0.7;
      case 'speaking':
        return 2.0;
      default:
        return 1;
    }
  }, [state]);

  // Emotion-based color intensity
  const emotionIntensity = useMemo(() => {
    switch (emotion) {
      case 'happy':
        return 1.25;
      case 'curious':
        return 1.15;
      case 'focused':
        return 0.95;
      default:
        return 1;
    }
  }, [emotion]);

  const { container } = sizes[size];

  const styleVars = useMemo(() => {
    return {
      '--orbWave': waveSpeed,
    } as CSSProperties;
  }, [waveSpeed]);

  // Stable unique ID for this instance
  const orbId = useId();

  return (
    <div
      className={cn(
        'relative flex items-center justify-center cursor-pointer',
        'transition-transform duration-300',
        container,
        stateAnimations,
        onClick && 'hover:scale-105 active:scale-95',
        className
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      style={styleVars}
    >
      {/* Glow effects - all states rendered with opacity transition */}
      {STATES.map((s) => (
        <div
          key={s}
          className={cn(
            'absolute inset-0 rounded-full blur-2xl',
            'transition-opacity duration-[5000ms] ease-in-out',
            'bg-gradient-to-tr',
            STATE_PALETTES[s].glow
          )}
          style={{
            opacity: state === s ? (s === 'idle' ? 0.5 : s === 'speaking' ? 0.85 : 0.7) : 0,
            transform: `scale(${emotionIntensity})`,
          }}
        />
      ))}

      {/* Main SVG */}
      <svg
        viewBox="0 0 100 100"
        className="relative z-10 w-full h-full drop-shadow-2xl"
        style={{ filter: `saturate(${emotionIntensity * 1.1})` }}
      >
        <defs>
          {/* Clip path for the main circle */}
          <clipPath id={`${orbId}-clip`}>
            <circle cx="50" cy="50" r="50" />
          </clipPath>

          {/* Shimmer layer - shared */}
          <radialGradient id={`${orbId}-shimmer`} cx="65%" cy="20%" r="60%">
            <stop offset="0%" stopColor="white" stopOpacity="0.7" />
            <stop offset="25%" stopColor="white" stopOpacity="0.3" />
            <stop offset="100%" stopColor="white" stopOpacity="0" />
          </radialGradient>

          {/* Depth gradient - shared */}
          <radialGradient id={`${orbId}-depth`} cx="50%" cy="45%" r="62%">
            <stop offset="0%" stopColor="white" stopOpacity="0" />
            <stop offset="75%" stopColor="white" stopOpacity="0.05" />
            <stop offset="100%" stopColor="black" stopOpacity="0.25" />
          </radialGradient>

          {/* Glossy highlight - shared */}
          <radialGradient id={`${orbId}-gloss`} cx="32%" cy="18%" r="55%">
            <stop offset="0%" stopColor="white" stopOpacity="0.6" />
            <stop offset="30%" stopColor="white" stopOpacity="0.2" />
            <stop offset="100%" stopColor="white" stopOpacity="0" />
          </radialGradient>

          {/* Grain filter */}
          <filter id={`${orbId}-grain`}>
            <feTurbulence type="fractalNoise" baseFrequency="0.7" numOctaves="3" result="grain" />
            <feColorMatrix type="saturate" values="0" />
            <feBlend in="SourceGraphic" mode="overlay" />
          </filter>
        </defs>

        <g clipPath={`url(#${orbId}-clip)`}>
          {/* Render all state layers - only active one is visible */}
          {STATES.map((s) => (
            <StateLayer
              key={s}
              orbId={orbId}
              stateName={s}
              palette={STATE_PALETTES[s]}
              isActive={state === s}
            />
          ))}

          {/* Shimmer - always visible */}
          <g className="orb-grad-layer orb-grad-5" style={{ mixBlendMode: 'screen' }}>
            <circle cx="50" cy="50" r="50" fill={`url(#${orbId}-shimmer)`} opacity="0.6" />
          </g>

          {/* Noise texture overlay */}
          <rect
            width="100"
            height="100"
            fill="#888"
            opacity="0.06"
            filter={`url(#${orbId}-grain)`}
            style={{ mixBlendMode: 'overlay' }}
          />

          {/* Depth and gloss - always visible */}
          <circle cx="50" cy="50" r="52" fill={`url(#${orbId}-gloss)`} style={{ mixBlendMode: 'overlay' }} />
          <circle cx="50" cy="50" r="50" fill={`url(#${orbId}-depth)`} style={{ mixBlendMode: 'multiply' }} />
        </g>

        {/* Outer rim highlight */}
        <circle cx="50" cy="50" r="49.5" fill="none" stroke="white" strokeOpacity="0.15" strokeWidth="0.5" />
        <circle cx="50" cy="50" r="48.5" fill="none" stroke="white" strokeOpacity="0.08" strokeWidth="1" />
      </svg>
    </div>
  );
});

export { AnimatedOrb };