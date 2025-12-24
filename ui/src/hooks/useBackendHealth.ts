/**
 * useBackendHealth Hook
 *
 * Monitors backend health status and provides connection state.
 * Automatically retries on failure and provides user feedback.
 */

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiClient } from '@/lib/api-client';

export type BackendStatus = 'checking' | 'connected' | 'disconnected' | 'error';

interface UseBackendHealthOptions {
  /** Check health on mount (default: true) */
  checkOnMount?: boolean;
  /** Auto-retry interval in ms when disconnected (default: 10000) */
  retryInterval?: number;
  /** Number of retries before giving up (default: 3) */
  maxRetries?: number;
}

interface UseBackendHealthReturn {
  /** Current backend connection status */
  status: BackendStatus;
  /** Whether the backend is ready to accept requests */
  isReady: boolean;
  /** Last error message if any */
  error: string | null;
  /** Manually trigger a health check */
  checkHealth: () => Promise<boolean>;
  /** Reset error state and retry */
  retry: () => void;
}

export function useBackendHealth({
  checkOnMount = true,
  retryInterval = 10000,
  maxRetries = 3,
}: UseBackendHealthOptions = {}): UseBackendHealthReturn {
  const [status, setStatus] = useState<BackendStatus>('checking');
  const [error, setError] = useState<string | null>(null);
  
  const retriesRef = useRef(0);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const checkHealth = useCallback(async (): Promise<boolean> => {
    try {
      setStatus('checking');
      setError(null);
      
      const response = await apiClient.healthCheck();
      
      if (response.status === 'healthy') {
        setStatus('connected');
        retriesRef.current = 0;
        return true;
      } else {
        setStatus('error');
        setError('Backend reported unhealthy status');
        return false;
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to connect to backend';
      setError(errorMessage);
      
      // Determine if we should show disconnected or error
      if (errorMessage.toLowerCase().includes('network') || 
          errorMessage.toLowerCase().includes('fetch') ||
          errorMessage.toLowerCase().includes('timeout')) {
        setStatus('disconnected');
      } else {
        setStatus('error');
      }
      
      return false;
    }
  }, []);

  const retry = useCallback(() => {
    retriesRef.current = 0;
    setError(null);
    checkHealth();
  }, [checkHealth]);

  // Initial health check
  useEffect(() => {
    if (checkOnMount) {
      checkHealth();
    }
  }, [checkOnMount, checkHealth]);

  // Auto-retry when disconnected
  useEffect(() => {
    if (status === 'disconnected' && retriesRef.current < maxRetries) {
      retryTimeoutRef.current = setTimeout(() => {
        retriesRef.current += 1;
        checkHealth();
      }, retryInterval);
    }

    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, [status, retryInterval, maxRetries, checkHealth]);

  return {
    status,
    isReady: status === 'connected',
    error,
    checkHealth,
    retry,
  };
}
