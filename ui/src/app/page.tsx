/**
 * Home Page - Redesigned
 *
 * Modern landing page with hero section, mode selection, and chat interface.
 * Features acrylic effects, floating elements, and smooth transitions.
 */

'use client';

import { useState, useCallback, useEffect } from 'react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { useRouter } from 'next/navigation';
import { HeroSection } from '@/components/landing/HeroSection';
import { FloatingSidebar } from '@/components/layout/FloatingSidebar';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { useSessions } from '@/hooks/useSessions';
import { useChat } from '@/hooks/useChat';
import { getFriendlyError } from '@/lib/errors';
import { type ChatMode } from '@/lib/config';

export default function HomePage() {
  const router = useRouter();
  const [hasStarted, setHasStarted] = useState(false);
  const [selectedMode, setSelectedMode] = useState<ChatMode>('chat');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isSending, setIsSending] = useState(false);

  const {
    sessions,
    activeSessionId,
    createNewSession,
    selectSession,
    removeSession,
    renameCurrentSession,
    refreshSessions,
  } = useSessions();

  // Handle errors
  const handleError = useCallback((error: Error) => {
    const friendly = getFriendlyError(error);
    toast.error(friendly.title, {
      description: friendly.message,
    });
  }, []);

  // Chat hook for active session
  const {
    messages,
    isLoading: chatLoading,
    sendMessage,
    regenerateMessage,
  } = useChat({
    sessionId: activeSessionId || '',
    onError: handleError,
  });

  // Handle mode selection from hero
  const handleModeSelect = (mode: ChatMode) => {
    setSelectedMode(mode);
  };

  // Handle start from hero
  const handleStart = useCallback(async () => {
    setHasStarted(true);
    
    // Navigate to appropriate page based on mode
    if (selectedMode === 'voice' || selectedMode === 'conversation') {
      router.push(`/voice?mode=${selectedMode === 'conversation' ? 'continuous' : 'push-to-talk'}`);
    }
  }, [selectedMode, router]);

  // Keyboard shortcut to start
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!hasStarted && e.key === 'Enter') {
        handleStart();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [hasStarted, handleStart]);

  // Handle new chat
  const handleNewChat = async () => {
    try {
      await createNewSession();
    } catch {
      toast.error('Failed to create new chat');
    }
  };

  // Handle send message
  const handleSendMessage = async (content: string) => {
    if (isSending) return;
    
    try {
      setIsSending(true);
      
      if (!activeSessionId) {
        const newSession = await createNewSession();
        if (newSession?.id) {
          await sendMessage(content, newSession.id);
        }
      } else {
        await sendMessage(content);
      }
      
      await refreshSessions();
    } finally {
      setIsSending(false);
    }
  };

  // Handle session delete
  const handleDeleteSession = async (id: string) => {
    try {
      await removeSession(id);
      toast.success('Chat deleted');
    } catch {
      toast.error('Failed to delete chat');
    }
  };

  // Handle session rename
  const handleRenameSession = async (id: string, title: string) => {
    try {
      await renameCurrentSession(id, title);
      toast.success('Chat renamed');
    } catch {
      toast.error('Failed to rename chat');
    }
  };

  // Show hero/landing if not started
  if (!hasStarted) {
    return (
      <div className="flex-1 min-h-0 overflow-y-auto">
        <HeroSection
          onModeSelect={handleModeSelect}
          onStart={handleStart}
        />
      </div>
    );
  }

  // Show chat interface for text chat mode
  return (
    <div className="flex-1 min-h-0 flex">
      {/* Floating Sidebar */}
      <FloatingSidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={selectSession}
        onNewSession={handleNewChat}
        onDeleteSession={handleDeleteSession}
        onRenameSession={handleRenameSession}
      />

      {/* Main Content */}
      <main
        className={cn(
          'flex-1 flex flex-col min-h-0 overflow-hidden transition-all duration-300',
          sidebarOpen ? 'lg:ml-96' : ''
        )}
      >
        <ChatInterface
          messages={messages}
          isLoading={chatLoading || isSending}
          onSend={handleSendMessage}
          onRegenerate={regenerateMessage}
          activeSessionId={activeSessionId}
        />
      </main>
    </div>
  );
}
