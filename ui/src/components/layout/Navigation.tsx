/**
 * Navigation Component
 *
 * Modern floating navigation bar with acrylic effect.
 */

'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  MessageSquare,
  Mic,
  Moon,
  Sun,
  Monitor,
  Menu,
  X,
} from 'lucide-react';
import { useState } from 'react';
import { Logo } from '@/components/layout/Logo';

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { href: '/', label: 'Chat', icon: <MessageSquare className="w-5 h-5" /> },
  { href: '/voice', label: 'Voice', icon: <Mic className="w-5 h-5" /> },
];

interface NavigationProps {
  theme: 'light' | 'dark' | 'system';
  onThemeChange: (theme: 'light' | 'dark' | 'system') => void;
}

const Navigation = ({ theme, onThemeChange }: NavigationProps) => {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const toggleTheme = () => {
    if (theme === 'light') {
      onThemeChange('dark');
    } else if (theme === 'dark') {
      onThemeChange('system');
    } else {
      onThemeChange('light');
    }
  };

  const ThemeIcon = theme === 'dark' ? Moon : theme === 'system' ? Monitor : Sun;

  return (
    <header className="sticky top-0 z-40 p-4">
      <nav
        className={cn(
          'max-w-7xl mx-auto px-4 sm:px-6',
          'rounded-2xl',
          'bg-white/70 dark:bg-neutral-900/70',
          'backdrop-blur-xl',
          'border border-white/30 dark:border-white/10',
          'shadow-lg shadow-black/5 dark:shadow-black/20'
        )}
      >
        <div className="flex items-center justify-between h-14">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 flex-shrink-0">
            <Logo size="sm" showText={false} />
            <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
              LankaTel AI Assistant
            </span>
          </Link>

          {/* Desktop navigation */}
          <div className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-2 px-4 py-2 rounded-full',
                    'text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'bg-primary-500/10 text-primary-600 dark:text-primary-400'
                      : 'text-neutral-600 hover:bg-neutral-100/50 dark:text-neutral-400 dark:hover:bg-neutral-800/50'
                  )}
                  aria-current={isActive ? 'page' : undefined}
                >
                  {item.icon}
                  {item.label}
                </Link>
              );
            })}
          </div>

          {/* Right side */}
          <div className="flex items-center gap-2">
            {/* Theme toggle */}
            <button
              onClick={toggleTheme}
              className={cn(
                'p-2.5 rounded-full',
                'hover:bg-neutral-100/50 dark:hover:bg-neutral-800/50',
                'transition-all duration-200'
              )}
              aria-label={`Current theme: ${theme}. Click to toggle.`}
            >
              <ThemeIcon className="w-5 h-5 text-neutral-600 dark:text-neutral-400" />
            </button>

            {/* Mobile menu button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className={cn(
                'md:hidden p-2.5 rounded-full',
                'hover:bg-neutral-100/50 dark:hover:bg-neutral-800/50',
                'transition-all duration-200'
              )}
              aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
            >
              {mobileMenuOpen ? (
                <X className="w-5 h-5 text-neutral-600 dark:text-neutral-400" />
              ) : (
                <Menu className="w-5 h-5 text-neutral-600 dark:text-neutral-400" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile navigation */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-neutral-200/50 dark:border-neutral-700/50 animate-slide-down">
            <div className="flex flex-col gap-1">
              {navItems.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      'flex items-center gap-3 px-4 py-3 rounded-xl',
                      'text-base font-medium transition-all duration-200',
                      isActive
                        ? 'bg-primary-500/10 text-primary-600 dark:text-primary-400'
                        : 'text-neutral-600 hover:bg-neutral-100/50 dark:text-neutral-400 dark:hover:bg-neutral-800/50'
                    )}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    {item.icon}
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        )}
      </nav>
    </header>
  );
};

export { Navigation };
