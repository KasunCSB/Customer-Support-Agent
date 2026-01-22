/**
 * Home Page - Redesigned
 *
 * Modern landing page with hero section, mode selection, and chat interface.
 * Features acrylic effects, floating elements, and smooth transitions.
 */

'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { useRouter } from 'next/navigation';
import { HeroSection } from '@/components/landing/HeroSection';
import { FloatingSidebar } from '@/components/layout/FloatingSidebar';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { AgenticPanel } from '@/components/chat/AgenticPanel';
import { useSessions } from '@/hooks/useSessions';
import { useChat } from '@/hooks/useChat';
import { useAuthSession } from '@/hooks/useAuthSession';
import { apiClient, APIClientError } from '@/lib/api-client';
import { getFriendlyError } from '@/lib/errors';
import { type ChatModeId } from '@/lib/config';
import type { QuickAction } from '@/types/api';

export default function HomePage() {
  const router = useRouter();
  const [hasStarted, setHasStarted] = useState(false);
  const [selectedMode, setSelectedMode] = useState<ChatModeId>('chat');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [phone, setPhone] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [otpStatus, setOtpStatus] = useState('');
  const [otpStep, setOtpStep] = useState<'phone' | 'code'>('phone');
  const [verificationRequired, setVerificationRequired] = useState(false);
  const [agenticActions, setAgenticActions] = useState<QuickAction[]>([]);
  const [loadingAgenticActions, setLoadingAgenticActions] = useState(false);
  const { token, setToken } = useAuthSession();
  const loadedActionsTokenRef = useRef<string | null>(null);

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
    showWorking,
    needsVerification,
    sendMessage,
    regenerateMessage,
  } = useChat({
    sessionId: activeSessionId || '',
    onError: handleError,
  });

  useEffect(() => {
    setVerificationRequired(Boolean(needsVerification) && !token);
  }, [needsVerification, token]);

  useEffect(() => {
    setVerificationRequired(false);
    setOtpStep('phone');
    setOtpCode('');
    setOtpStatus('');
  }, [activeSessionId]);

  const loadAgenticActions = useCallback(async () => {
    if (!token) return;
    setLoadingAgenticActions(true);
    try {
      const data = await apiClient.getAgenticContext({ authToken: token });
      setAgenticActions(data.quick_actions || []);
    } catch (err) {
      console.error('Failed to load quick actions:', err);
      setAgenticActions([]);
      if (err instanceof APIClientError && /unauthorized|invalid or expired session/i.test(err.message)) {
        setToken(null);
      }
    } finally {
      setLoadingAgenticActions(false);
    }
  }, [token, setToken]);

  useEffect(() => {
    if (!token) {
      setAgenticActions([]);
      loadedActionsTokenRef.current = null;
      setOtpStep('phone');
      setOtpCode('');
      setVerificationRequired(false);
      return;
    }
    if (loadedActionsTokenRef.current === token) {
      return;
    }
    loadedActionsTokenRef.current = token;
    loadAgenticActions();
  }, [token, loadAgenticActions]);

  // Handle mode selection from hero
  const handleModeSelect = (mode: ChatModeId) => {
    setSelectedMode(mode);
  };

  // Handle start from hero
  const handleStart = useCallback(async () => {
    setHasStarted(true);
    
    // Navigate to appropriate page based on mode
    if (selectedMode === 'voice' || selectedMode === 'realtime') {
      router.push(`/voice?mode=${selectedMode === 'realtime' ? 'continuous' : 'push-to-talk'}`);
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

  const startOtp = async () => {
    const cleaned = phone.replace(/[\s\-()]/g, '');
    if (!/^\+?\d{9,15}$/.test(cleaned)) {
      setOtpStatus('Enter a valid mobile number.');
      return;
    }
    try {
      setOtpStatus(`Sending code to ${cleaned}...`);
      await apiClient.startPhoneOtp(cleaned);
      setOtpStatus(`Code sent to ${cleaned}. Check the email on file.`);
      setOtpStep('code');
    } catch (err) {
      setOtpStatus(err instanceof Error ? err.message : 'Failed to send code');
    }
  };

  const confirmOtp = async () => {
    if (!otpCode.trim()) {
      setOtpStatus('Enter the verification code.');
      return;
    }
    try {
      setOtpStatus('Verifying...');
      const cleaned = phone.replace(/[\s\-()]/g, '');
      const data = await apiClient.confirmPhoneOtp(cleaned, otpCode.trim());
      setToken(data.token);
      setOtpStatus('Verified. Session active.');
      setOtpStep('phone');
    } catch (err) {
      setOtpStatus(err instanceof Error ? err.message : 'Verification failed');
    }
  };

  const handleQuickAction = async (action: QuickAction) => {
    if (!action.message) return;
    await handleSendMessage(action.message);
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
  const shouldShowAgenticPanel = verificationRequired || Boolean(token);

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
          showWorking={showWorking}
          agenticPanel={
            shouldShowAgenticPanel ? (
              <AgenticPanel
                needsVerification={verificationRequired}
                isVerified={Boolean(token)}
                otpStep={otpStep}
                phone={phone}
                code={otpCode}
                status={otpStatus}
                onPhoneChange={setPhone}
                onCodeChange={setOtpCode}
                onStartOtp={startOtp}
                onConfirmOtp={confirmOtp}
                quickActions={agenticActions}
                isLoadingActions={loadingAgenticActions}
                onQuickAction={handleQuickAction}
              />
            ) : null
          }
          onSend={handleSendMessage}
          onRegenerate={regenerateMessage}
          activeSessionId={activeSessionId}
        />
      </main>
    </div>
  );
}
