/**
 * Connection Status Component
 *
 * Displays backend connection status with appropriate messaging.
 * Shows a banner when disconnected or an error occurs.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { AlertTriangle, RefreshCw, WifiOff, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import type { BackendStatus } from '@/hooks/useBackendHealth';

interface ConnectionStatusProps {
  status: BackendStatus;
  error: string | null;
  onRetry: () => void;
  className?: string;
}

const ConnectionStatus = memo(function ConnectionStatus({
  status,
  error,
  onRetry,
  className,
}: ConnectionStatusProps) {
  // Don't render anything if connected
  if (status === 'connected') {
    return null;
  }

  // Show minimal loading state during initial check
  if (status === 'checking') {
    return (
      <div
        className={cn(
          'flex items-center justify-center gap-2 py-2 px-4',
          'bg-neutral-100 dark:bg-neutral-800',
          'text-neutral-600 dark:text-neutral-400 text-sm',
          className
        )}
      >
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>Connecting to server...</span>
      </div>
    );
  }

  // Disconnected or error state
  const isDisconnected = status === 'disconnected';

  return (
    <div
      className={cn(
        'flex items-center justify-between gap-4 py-3 px-4',
        isDisconnected
          ? 'bg-warning-50 dark:bg-warning-900/20 border-b border-warning-200 dark:border-warning-800'
          : 'bg-error-50 dark:bg-error-900/20 border-b border-error-200 dark:border-error-800',
        className
      )}
    >
      <div className="flex items-center gap-3">
        {isDisconnected ? (
          <WifiOff className="w-5 h-5 text-warning-600 dark:text-warning-400" />
        ) : (
          <AlertTriangle className="w-5 h-5 text-error-600 dark:text-error-400" />
        )}
        <div>
          <p
            className={cn(
              'font-medium text-sm',
              isDisconnected
                ? 'text-warning-800 dark:text-warning-200'
                : 'text-error-800 dark:text-error-200'
            )}
          >
            {isDisconnected ? 'Connection Lost' : 'Connection Error'}
          </p>
          <p
            className={cn(
              'text-xs',
              isDisconnected
                ? 'text-warning-600 dark:text-warning-400'
                : 'text-error-600 dark:text-error-400'
            )}
          >
            {error || (isDisconnected 
              ? 'Unable to reach the server. Retrying...' 
              : 'Something went wrong. Please try again.')}
          </p>
        </div>
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={onRetry}
        leftIcon={<RefreshCw className="w-3 h-3" />}
        className={cn(
          'shrink-0',
          isDisconnected
            ? 'border-warning-300 dark:border-warning-700 hover:bg-warning-100 dark:hover:bg-warning-900/30'
            : 'border-error-300 dark:border-error-700 hover:bg-error-100 dark:hover:bg-error-900/30'
        )}
      >
        Retry
      </Button>
    </div>
  );
});

export { ConnectionStatus };
