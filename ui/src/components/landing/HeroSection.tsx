/**
 * Hero Section Component
 *
 * Landing hero with dynamic welcome message from backend (RAG/LLM generated).
 * Features animated orb logo, hero text, and mode selection.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { AnimatedOrb } from '@/components/ui/AnimatedOrb';
import { ModeSwitcher } from '@/components/ui/ModeSwitcher';
import { APP_CONFIG, type ChatModeId } from '@/lib/config';
import { apiClient } from '@/lib/api-client';

interface HeroSectionProps {
  onModeSelect: (mode: ChatModeId) => void;
  onStart: () => void;
  className?: string;
}

const MAX_WELCOME_LEN = 56;

// Default welcome messages as fallback - tailored for LankaTel customer support
const DEFAULT_WELCOMES = [
  'How can I help with your LankaTel service today?',
  'Welcome to LankaTel support. What can I do for you?',
  'Need help with your mobile or broadband? Ask away.',
  "Let's resolve your LankaTel query together.",
];

function normalizeWelcomeText(input: string): string {
  const raw = (input || '').replace(/\s+/g, ' ').trim();
  if (!raw) return DEFAULT_WELCOMES[0];

  // Prefer the first sentence/clause.
  const firstSentence = raw.split(/[.!?\n]/)[0]?.trim() || raw;
  const trimmed = firstSentence.replace(/^[\u2014\-\s]+/, '').trim();

  // Keep it short so it never blows out the hero.
  const maxLen = MAX_WELCOME_LEN;
  if (trimmed.length <= maxLen) return trimmed;

  // Try to cut at a word boundary.
  const sliced = trimmed.slice(0, maxLen);
  const lastSpace = sliced.lastIndexOf(' ');
  return (lastSpace > 24 ? sliced.slice(0, lastSpace) : sliced).trim() + '…';
}

function getTimeGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

function stripGreetingPrefix(input: string): string {
  return input.replace(/^(hi|hello|hey|good morning|good afternoon|good evening)\b[:,!.\-\s]*/i, '').trim();
}

function buildTimeAwareWelcome(input: string): string {
  const normalized = normalizeWelcomeText(input);
  const cleaned = stripGreetingPrefix(normalized);
  const greeting = `${getTimeGreeting()}!`;

  if (!cleaned) return greeting;

  const combined = `${greeting} ${cleaned}`;
  if (combined.length <= MAX_WELCOME_LEN) return combined;

  const available = MAX_WELCOME_LEN - greeting.length - 1;
  if (available <= 0) return greeting;

  let trimmed = cleaned.slice(0, available).trim();
  const lastSpace = trimmed.lastIndexOf(' ');
  if (lastSpace > Math.max(18, Math.floor(available * 0.6))) {
    trimmed = trimmed.slice(0, lastSpace).trim();
  }
  if (trimmed.length < cleaned.length) {
    trimmed = `${trimmed}...`;
  }

  return trimmed ? `${greeting} ${trimmed}` : greeting;
}

const HeroSection = ({ onModeSelect, onStart, className }: HeroSectionProps) => {
  const [welcomeText, setWelcomeText] = useState('');
  const [isLoadingWelcome, setIsLoadingWelcome] = useState(true);
  const [selectedMode, setSelectedMode] = useState<ChatModeId>('chat');

  // Fetch welcome message from backend
  const fetchWelcomeMessage = useCallback(async () => {
    try {
      setIsLoadingWelcome(true);
      const response = await apiClient.getWelcomeMessage();
      setWelcomeText(buildTimeAwareWelcome(response.message));
    } catch {
      // Fallback to random default message
      const randomIndex = Math.floor(Math.random() * DEFAULT_WELCOMES.length);
      setWelcomeText(buildTimeAwareWelcome(DEFAULT_WELCOMES[randomIndex]));
    } finally {
      setIsLoadingWelcome(false);
    }
  }, []);

  useEffect(() => {
    fetchWelcomeMessage();
  }, [fetchWelcomeMessage]);

  const handleModeSelect = (mode: ChatModeId) => {
    setSelectedMode(mode);
    onModeSelect(mode);
  };

  const handleStart = () => {
    onStart();
  };

  return (
    <div
      className={cn(
        // Scroll within the hero (not the whole app shell) to avoid clipping on short viewports.
        'flex flex-col items-center justify-start flex-1 min-h-0 w-full overflow-y-auto',
        'px-4 pt-8 pb-10 sm:pt-10',
        'animate-fade-in',
        className
      )}
    >
      {/* Animated Orb Logo */}
      <div className="mb-5 sm:mb-6 scale-90 sm:scale-95 md:scale-100 animate-fade-in">
        <AnimatedOrb
          size="xl"
          state="idle"
          enableBreathing={true}
          enableParticles={false}
          onClick={handleStart}
        />
      </div>

      {/* Hero Text */}
      <div className="text-center max-w-2xl mb-5 sm:mb-6 space-y-3 sm:space-y-4 animate-fade-in">
        {/* Main welcome text - from backend */}
        <h1
          className={cn(
            'text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold',
            'bg-gradient-to-r from-primary-500 via-accent-500 to-secondary-500',
            'bg-clip-text text-transparent',
            'leading-[1.2] md:leading-[1.15]',
            'max-w-[18ch] md:max-w-[22ch] mx-auto',
            'text-balance',
            'pb-2',
            isLoadingWelcome && 'opacity-0'
          )}
        >
          {isLoadingWelcome ? 'Loading...' : welcomeText}
        </h1>

        {/* Sub-hero text - introducing the AI */}
        <p className="text-base sm:text-lg md:text-xl text-neutral-600 dark:text-neutral-400">
          I&apos;m {APP_CONFIG.name}, {APP_CONFIG.tagline.toLowerCase()}
        </p>
      </div>

      {/* Mode Selection Label */}
      <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-3 sm:mb-4 uppercase tracking-wider animate-fade-in">
        Choose how you&apos;d like to interact
      </p>

      {/* Mode Switcher */}
      <div className="mb-6 sm:mb-8 animate-fade-in">
        <ModeSwitcher value={selectedMode} onChange={handleModeSelect} />
      </div>

      {/* Start Button */}
      <button
        onClick={handleStart}
        className={cn(
          'px-8 py-4 rounded-full',
          'bg-gradient-to-r from-primary-500 to-accent-500',
          'text-white font-semibold text-lg',
          'shadow-lg shadow-primary-500/30',
          'hover:shadow-xl hover:shadow-primary-500/40',
          'hover:scale-105 active:scale-95',
          'transition-all duration-300',
          'animate-fade-in'
        )}
      >
        Get Started
      </button>

    </div>
  );
};

export { HeroSection };
