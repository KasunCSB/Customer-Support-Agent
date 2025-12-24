/**
 * Global Error Page
 *
 * This is a fallback error boundary that catches errors in the root layout.
 * Must include its own html and body tags since it replaces the entire page.
 */

'use client';

import { useEffect } from 'react';

interface GlobalErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function GlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    // Log the error to console
    console.error('Global application error:', error);
  }, [error]);

  return (
    <html lang="en">
      <body className="font-sans">
        <div 
          className="min-h-screen flex items-center justify-center p-4"
          style={{
            background: 'linear-gradient(to bottom right, #fafafa, #f5f5f5)',
          }}
        >
          <div className="text-center max-w-md mx-auto">
            {/* Error icon */}
            <div className="relative w-32 h-32 mx-auto mb-8">
              <div 
                className="absolute inset-0 rounded-full animate-pulse"
                style={{
                  background: 'linear-gradient(to bottom right, #f87171, #dc2626)',
                  opacity: 0.2,
                }}
              />
              <div 
                className="absolute inset-4 rounded-full animate-pulse"
                style={{
                  background: 'linear-gradient(to bottom right, #ef4444, #b91c1c)',
                  opacity: 0.4,
                  animationDelay: '75ms',
                }}
              />
              <div 
                className="absolute inset-8 rounded-full flex items-center justify-center"
                style={{
                  background: 'linear-gradient(to bottom right, #dc2626, #991b1b)',
                }}
              >
                <svg
                  className="w-10 h-10"
                  fill="none"
                  stroke="white"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
            </div>

            {/* Content */}
            <h1 
              className="text-2xl font-semibold mb-3"
              style={{ color: '#171717' }}
            >
              Critical Error
            </h1>
            <p 
              className="mb-2"
              style={{ color: '#525252' }}
            >
              A critical error has occurred. Please refresh the page to continue.
            </p>
            {error.digest && (
              <p 
                className="text-xs mb-6 font-mono"
                style={{ color: '#737373' }}
              >
                Error ID: {error.digest}
              </p>
            )}

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                onClick={reset}
                className="inline-flex items-center justify-center px-6 py-3 rounded-xl text-white font-medium transition-colors"
                style={{
                  backgroundColor: '#2563eb',
                  boxShadow: '0 10px 15px -3px rgba(37, 99, 235, 0.25)',
                }}
                onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#1d4ed8'}
                onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#2563eb'}
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
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                Try Again
              </button>
              {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
              <a
                href="/"
                className="inline-flex items-center justify-center px-6 py-3 rounded-xl font-medium transition-colors"
                style={{
                  backgroundColor: 'white',
                  color: '#404040',
                  border: '1px solid #e5e5e5',
                }}
                onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f5f5f5'}
                onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'white'}
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
              </a>
            </div>

            {/* Help text */}
            <p 
              className="mt-8 text-sm"
              style={{ color: '#737373' }}
            >
              If this problem persists, please clear your browser cache and try again.
            </p>

            {/* Subtle branding */}
            <p 
              className="mt-8 text-sm"
              style={{ color: '#737373' }}
            >
              LankaTel AI Assistant
            </p>
          </div>
        </div>
      </body>
    </html>
  );
}
