/**
 * Logo Component
 *
 * Custom SVG logo representing AI knowledge and conversation.
 */

import { cn } from '@/lib/utils';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
  className?: string;
}

const Logo = ({ size = 'md', showText = true, className }: LogoProps) => {
  const sizes = {
    sm: { icon: 24, text: 'text-sm' },
    md: { icon: 32, text: 'text-base' },
    lg: { icon: 48, text: 'text-xl' },
  };

  const { icon, text } = sizes[size];

  return (
    <div className={cn('flex items-center gap-2', className)}>
      {/* SVG Logo - Simple circular gradient orb */}
      <svg
        width={icon}
        height={icon}
        viewBox="0 0 32 32"
        xmlns="http://www.w3.org/2000/svg"
        className="flex-shrink-0"
      >
        <defs>
          <linearGradient id="logo-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style={{ stopColor: '#3B82F6', stopOpacity: 1 }} />
            <stop offset="50%" style={{ stopColor: '#8B5CF6', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: '#EC4899', stopOpacity: 1 }} />
          </linearGradient>
          <filter id="logo-glow">
            <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        <circle cx="16" cy="16" r="14" fill="url(#logo-grad)" filter="url(#logo-glow)"/>
      </svg>

      {/* Text */}
      {showText && (
        <div className="flex flex-col">
          <span
            className={cn(
              'font-semibold text-neutral-900 dark:text-neutral-100 leading-tight',
              text
            )}
          >
            Support Agent
          </span>
          <span className="text-2xs text-neutral-500 dark:text-neutral-400">
            AI-Powered
          </span>
        </div>
      )}
    </div>
  );
};

export { Logo };
