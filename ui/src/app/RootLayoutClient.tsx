/**
 * Root Layout Client Component
 *
 * Client-side wrapper with providers and global components.
 * Includes backend health monitoring and connection status display.
 */

'use client';

import { ReactNode, createContext, useContext } from 'react';
import { usePathname } from 'next/navigation';
import { Toaster } from 'sonner';
import { ThemeProvider, useTheme } from '@/components/providers/ThemeProvider';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { Navigation } from '@/components/layout/Navigation';
import { ConnectionStatus } from '@/components/ui/ConnectionStatus';
import { useBackendHealth, type BackendStatus } from '@/hooks/useBackendHealth';

// Context to share backend health status across the app
interface BackendHealthContextValue {
  status: BackendStatus;
  isReady: boolean;
  error: string | null;
  checkHealth: () => Promise<boolean>;
  retry: () => void;
}

const BackendHealthContext = createContext<BackendHealthContextValue | null>(null);

export function useBackendHealthContext() {
  const context = useContext(BackendHealthContext);
  if (!context) {
    throw new Error('useBackendHealthContext must be used within RootLayoutClient');
  }
  return context;
}

function RootLayoutInner({ children }: { children: ReactNode }) {
  const { theme, setTheme } = useTheme();
  const backendHealth = useBackendHealth({
    checkOnMount: true,
    retryInterval: 10000,
    maxRetries: 3,
  });
  const pathname = usePathname();
  const hideNavigation = pathname?.startsWith('/admin');

  return (
    <BackendHealthContext.Provider value={backendHealth}>
      <div className="min-h-screen flex flex-col overflow-hidden">
        {!hideNavigation && <Navigation theme={theme} onThemeChange={setTheme} />}
        {!hideNavigation && (
          <ConnectionStatus
            status={backendHealth.status}
            error={backendHealth.error}
            onRetry={backendHealth.retry}
          />
        )}
        <main className="flex-1 flex flex-col min-h-0 overflow-hidden">{children}</main>
        <Toaster
          position="top-right"
          toastOptions={{
            className:
              'bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 border border-neutral-200 dark:border-neutral-700',
            duration: 4000,
          }}
        />
      </div>
    </BackendHealthContext.Provider>
  );
}

export function RootLayoutClient({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="system">
        <RootLayoutInner>{children}</RootLayoutInner>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
