/**
 * useSessions Hook
 *
 * Manages chat session state and persistence.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  getAllSessions,
  createSession,
  deleteSession,
  renameSession,
  getSession,
} from '@/lib/storage';
import type { ChatSession } from '@/types/api';

interface UseSessionsReturn {
  sessions: ChatSession[];
  activeSession: ChatSession | null;
  activeSessionId: string | null;
  isLoading: boolean;
  createNewSession: (title?: string) => Promise<ChatSession>;
  selectSession: (id: string) => Promise<void>;
  removeSession: (id: string) => Promise<void>;
  renameCurrentSession: (id: string, title: string) => Promise<void>;
  refreshSessions: () => Promise<void>;
}

export function useSessions(): UseSessionsReturn {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load all sessions on mount
  const refreshSessions = useCallback(async () => {
    try {
      const allSessions = await getAllSessions();
      setSessions(allSessions);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      await refreshSessions();
      setIsLoading(false);
    };
    init();
  }, [refreshSessions]);

  // Load active session when ID changes
  useEffect(() => {
    const loadActive = async () => {
      if (!activeSessionId) {
        setActiveSession(null);
        return;
      }

      const session = await getSession(activeSessionId);
      setActiveSession(session);
    };
    loadActive();
  }, [activeSessionId]);

  // Create a new session
  const createNewSession = useCallback(async (title?: string) => {
    const session = await createSession(title);
    setSessions((prev) => [session, ...prev]);
    setActiveSessionId(session.id);
    setActiveSession(session);
    return session;
  }, []);

  // Select a session
  const selectSession = useCallback(async (id: string) => {
    setActiveSessionId(id);
    const session = await getSession(id);
    setActiveSession(session);
  }, []);

  // Delete a session
  const removeSession = useCallback(
    async (id: string) => {
      await deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));

      // If deleting active session, clear it
      if (activeSessionId === id) {
        setActiveSessionId(null);
        setActiveSession(null);
      }
    },
    [activeSessionId]
  );

  // Rename a session
  const renameCurrentSession = useCallback(async (id: string, title: string) => {
    const updated = await renameSession(id, title);
    if (updated) {
      setSessions((prev) =>
        prev.map((s) => (s.id === id ? { ...s, title } : s))
      );
      if (activeSessionId === id) {
        setActiveSession((prev) => (prev ? { ...prev, title } : null));
      }
    }
  }, [activeSessionId]);

  return {
    sessions,
    activeSession,
    activeSessionId,
    isLoading,
    createNewSession,
    selectSession,
    removeSession,
    renameCurrentSession,
    refreshSessions,
  };
}
