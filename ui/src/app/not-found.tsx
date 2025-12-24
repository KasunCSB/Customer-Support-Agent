/**
 * Custom 404 Not Found Page
 *
 * Displayed when a route doesn't exist. Matches the app's design language.
 */

import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-neutral-50 to-neutral-100 dark:from-neutral-950 dark:to-neutral-900 p-4">
      <div className="text-center max-w-md mx-auto">
        {/* Animated orb decoration */}
        <div className="relative w-32 h-32 mx-auto mb-8">
          <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 opacity-20 animate-pulse" />
          <div className="absolute inset-4 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 opacity-40 animate-pulse delay-75" />
          <div className="absolute inset-8 rounded-full bg-gradient-to-br from-primary-600 to-primary-800 flex items-center justify-center">
            <span className="text-4xl font-bold text-white">404</span>
          </div>
        </div>

        {/* Content */}
        <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100 mb-3">
          Page Not Found
        </h1>
        <p className="text-neutral-600 dark:text-neutral-400 mb-8">
          Sorry, the page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/"
            className="inline-flex items-center justify-center px-6 py-3 rounded-xl bg-primary-600 text-white font-medium hover:bg-primary-700 transition-colors shadow-lg shadow-primary-500/25"
          >
            <svg
              className="w-5 h-5 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
              />
            </svg>
            Go Home
          </Link>
          <Link
            href="/voice"
            className="inline-flex items-center justify-center px-6 py-3 rounded-xl bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 font-medium hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors border border-neutral-200 dark:border-neutral-700"
          >
            <svg
              className="w-5 h-5 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
              />
            </svg>
            Talk to Rashmi
          </Link>
        </div>

        {/* Subtle branding */}
        <p className="mt-12 text-sm text-neutral-500 dark:text-neutral-500">
          LankaTel AI Assistant
        </p>
      </div>
    </div>
  );
}
