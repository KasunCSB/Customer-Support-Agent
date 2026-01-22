/**
 * useChat Hook
 *
 * Manages chat state, message handling, and API communication.
 */

'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { apiClient, APIClientError } from '@/lib/api-client';
import { useAuthSession } from '@/hooks/useAuthSession';
import {
  getSession,
  updateSession,
  addMessage as addMessageToStorage,
} from '@/lib/storage';
import type { Message } from '@/types/api';

interface UseChatOptions {
  sessionId: string;
  onError?: (error: Error) => void;
}

interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  showWorking: boolean;
  needsVerification: boolean;
  error: Error | null;
  sendMessage: (content: string, overrideSessionId?: string) => Promise<void>;
  regenerateMessage: (messageId: string) => Promise<void>;
  clearError: () => void;
  clearMessages: () => void;
}

export function useChat({ sessionId, onError }: UseChatOptions): UseChatReturn {
  const { token } = useAuthSession();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showWorking, setShowWorking] = useState(false);
  const [needsVerification, setNeedsVerification] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  
  // Track the last loaded session to prevent redundant loads
  const lastLoadedSessionRef = useRef<string | null>(null);
  const pendingSessionIdRef = useRef<string | null>(null);
  const activeMessagesSessionIdRef = useRef<string | null>(null);
  const optimisticSessionIdRef = useRef<string | null>(null);
  const messagesRef = useRef<Message[]>([]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  // Load messages from storage when session changes
  useEffect(() => {
    // No session - reset state
    if (!sessionId) {
      if (pendingSessionIdRef.current) {
        return;
      }
      setMessages([]);
      lastLoadedSessionRef.current = null;
      activeMessagesSessionIdRef.current = null;
      optimisticSessionIdRef.current = null;
      return;
    }
    
    // Same session already loaded - skip (handles override case)
    if (lastLoadedSessionRef.current === sessionId) {
      return;
    }

    // New session - load messages
    let cancelled = false;
    
    const loadMessages = async () => {
      try {
        const session = await getSession(sessionId);
        if (cancelled) return;
        
        // Only update if this is still the current session
        if (session?.messages && session.messages.length > 0) {
          if (
            activeMessagesSessionIdRef.current === sessionId &&
            messagesRef.current.length > session.messages.length
          ) {
            lastLoadedSessionRef.current = sessionId;
            return;
          }
          setMessages(session.messages);
          activeMessagesSessionIdRef.current = sessionId;
          pendingSessionIdRef.current = null;
          optimisticSessionIdRef.current = null;
        } else {
          if (optimisticSessionIdRef.current === sessionId) {
            lastLoadedSessionRef.current = sessionId;
            return;
          }
          if (activeMessagesSessionIdRef.current === sessionId && messagesRef.current.length > 0) {
            lastLoadedSessionRef.current = sessionId;
            return;
          }
          setMessages([]);
        }
        lastLoadedSessionRef.current = sessionId;
      } catch (err) {
        console.error('Failed to load messages:', err);
        if (!cancelled) {
          setMessages([]);
        }
      }
    };
    
    loadMessages();
    
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  useEffect(() => {
    if (token) {
      setNeedsVerification(false);
    }
  }, [token]);

  // Send a message - accepts optional overrideSessionId for when session was just created
  const sendMessage = useCallback(
    async (content: string, overrideSessionId?: string) => {
      const effectiveSessionId = overrideSessionId || sessionId;
      
      if (!content.trim() || isLoading) return;
      if (!effectiveSessionId) {
        console.error('No session ID available');
        return;
      }
      
      // Mark that we're adding messages - prevents reload from overwriting
      if (overrideSessionId) {
        lastLoadedSessionRef.current = overrideSessionId;
      }
      pendingSessionIdRef.current = effectiveSessionId;
      activeMessagesSessionIdRef.current = effectiveSessionId;
      optimisticSessionIdRef.current = effectiveSessionId;

      const normalized = content.toLowerCase();
      const agenticIntent = [
        /\b(balance|account balance|check balance)\b/,
        /\b(create|open|raise|file)\b.*\bticket\b/,
        /\b(activate|enable|start|subscribe|buy|add)\b.*\b(service|plan|package|subscription|pack|vas|sms|voice|bundle)\b/,
        /\b(deactivate|disable|stop|cancel|remove)\b.*\b(service|plan|package|subscription|pack|vas|sms|voice|bundle)\b/,
        /\b(list|show|view)\b.*\b(subscriptions?|tickets?|actions?|activity|history)\b/,
        /\b(check|track)\b.*\b(ticket|subscription|status)\b/,
        /\b(connection|account)\b.*\b(info|information|details|status|validity|expiry|expires)\b/,
        /\b(recent|latest)\b.*\b(actions?|activity|requests|history)\b/,
        /\b(live agent|human agent|talk to (a )?agent|representative|customer care|call back|callback)\b/,
      ].some((pattern) => pattern.test(normalized));

      setShowWorking(agenticIntent);
      setIsLoading(true);
      setError(null);

      // Create user message
      const userMessage: Message = {
        id: uuidv4(),
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      };

      // Immediately add user message to state for swift UI response
      setMessages((prev: Message[]) => [...prev, userMessage]);

      // Create placeholder for assistant message with isStreaming flag
      const assistantMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        isStreaming: true,
      };

      setMessages((prev: Message[]) => [...prev, assistantMessage]);

      try {
        // Save user message to storage (non-blocking for UI)
        addMessageToStorage(effectiveSessionId, userMessage).catch((err) =>
          console.error('Failed to save user message:', err)
        );

        // Use non-streaming chat API instead of streaming for more reliable responses
        const response = await apiClient.chat(content, effectiveSessionId, {
          authToken: token || undefined,
        });
        setNeedsVerification(Boolean(response.needs_verification));

        // Finalize assistant message
        const finalMessage: Message = {
          ...assistantMessage,
          content: response.answer || 'I apologize, but I was unable to generate a response.',
          sources:
            response.sources && response.sources.length > 0
              ? response.sources.map((s) => ({ source: s.source, relevance: s.relevance || undefined }))
              : undefined,
          isStreaming: false,
        };

        setMessages((prev: Message[]) =>
          prev.map((m: Message) => (m.id === assistantMessage.id ? finalMessage : m))
        );

        // Save assistant message to storage (non-blocking)
        addMessageToStorage(effectiveSessionId, {
          role: 'assistant',
          content: finalMessage.content,
          sources: finalMessage.sources,
        }).catch((err) => console.error('Failed to save assistant message:', err));

        // Update session title if it's the first message (non-blocking)
        getSession(effectiveSessionId)
          .then((session) => {
            if (session && session.messages.length <= 2) {
              const title = content.slice(0, 50) + (content.length > 50 ? '...' : '');
              updateSession(effectiveSessionId, { title }).catch((err) =>
                console.error('Failed to update session title:', err)
              );
            }
          })
          .catch((err) => console.error('Failed to get session for title update:', err));
      } catch (err) {
        // Remove streaming message on error
        setMessages((prev: Message[]) => prev.filter((m: Message) => m.id !== assistantMessage.id));

        const error =
          err instanceof APIClientError
            ? err
            : new Error(err instanceof Error ? err.message : 'Failed to send message');

        setError(error);
        onError?.(error);
      } finally {
        setIsLoading(false);
        setShowWorking(false);
        if (pendingSessionIdRef.current === effectiveSessionId) {
          pendingSessionIdRef.current = null;
        }
        if (optimisticSessionIdRef.current === effectiveSessionId) {
          optimisticSessionIdRef.current = null;
        }
      }
    },
    [sessionId, isLoading, onError, token]
  );

  // Regenerate a message (re-query without duplicating user message)
  const regenerateMessage = useCallback(
    async (messageId: string) => {
      const messageIndex = messages.findIndex((m) => m.id === messageId);
      if (messageIndex === -1) return;

      // Find the user message before this assistant message
      const userMessageIndex = messageIndex - 1;
      if (userMessageIndex < 0 || messages[userMessageIndex].role !== 'user')
        return;

      const userMessage = messages[userMessageIndex];
      const effectiveSessionId = lastLoadedSessionRef.current || sessionId;

      if (!effectiveSessionId) return;

      const normalized = userMessage.content.toLowerCase();
      const agenticIntent = [
        /\b(balance|account balance|check balance)\b/,
        /\b(create|open|raise|file)\b.*\bticket\b/,
        /\b(activate|enable|start|subscribe|buy|add)\b.*\b(service|plan|package|subscription|pack|vas|sms|voice|bundle)\b/,
        /\b(deactivate|disable|stop|cancel|remove)\b.*\b(service|plan|package|subscription|pack|vas|sms|voice|bundle)\b/,
        /\b(list|show|view)\b.*\b(subscriptions?|tickets?|actions?|activity|history)\b/,
        /\b(check|track)\b.*\b(ticket|subscription|status)\b/,
        /\b(connection|account)\b.*\b(info|information|details|status|validity|expiry|expires)\b/,
        /\b(recent|latest)\b.*\b(actions?|activity|requests|history)\b/,
        /\b(live agent|human agent|talk to (a )?agent|representative|customer care|call back|callback)\b/,
      ].some((pattern) => pattern.test(normalized));

      setShowWorking(agenticIntent);
      setIsLoading(true);
      setError(null);

      // Replace the assistant message with a streaming placeholder
      const newAssistantMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        isStreaming: true,
      };

      // Remove old assistant message and add new streaming one
      setMessages((prev: Message[]) => 
        prev.map((m: Message) => (m.id === messageId ? newAssistantMessage : m))
      );

      try {
        // Re-query with the same user message content
        const response = await apiClient.chat(userMessage.content, effectiveSessionId, {
          authToken: token || undefined,
        });
        setNeedsVerification(Boolean(response.needs_verification));

        // Finalize assistant message
        const finalMessage: Message = {
          ...newAssistantMessage,
          content: response.answer || 'I apologize, but I was unable to generate a response.',
          sources:
            response.sources && response.sources.length > 0
              ? response.sources.map((s) => ({ source: s.source, relevance: s.relevance || undefined }))
              : undefined,
          isStreaming: false,
        };

        setMessages((prev: Message[]) =>
          prev.map((m: Message) => (m.id === newAssistantMessage.id ? finalMessage : m))
        );

        // Save updated assistant message to storage
        addMessageToStorage(effectiveSessionId, {
          role: 'assistant',
          content: finalMessage.content,
          sources: finalMessage.sources,
        }).catch((err) => console.error('Failed to save regenerated message:', err));
      } catch (err) {
        // Restore original message on error
        setMessages((prev: Message[]) =>
          prev.map((m: Message) => (m.id === newAssistantMessage.id ? messages[messageIndex] : m))
        );

        const error =
          err instanceof APIClientError
            ? err
            : new Error(err instanceof Error ? err.message : 'Failed to regenerate message');

        setError(error);
        onError?.(error);
      } finally {
        setIsLoading(false);
        setShowWorking(false);
      }
    },
    [messages, sessionId, onError, token]
  );

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Clear all messages
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    isLoading,
    showWorking,
    needsVerification,
    error,
    sendMessage,
    regenerateMessage,
    clearError,
    clearMessages,
  };
}
