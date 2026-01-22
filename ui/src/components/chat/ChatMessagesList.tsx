/**
 * Chat Messages List Component
 *
 * Modern scrollable list of chat messages with floating elements.
 */

'use client';

import { useRef, useEffect, useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { ArrowDown, Sparkles } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { AnimatedOrb } from '@/components/ui/AnimatedOrb';
import type { Message } from '@/types/api';
import type { ReactNode } from 'react';

interface ChatMessagesListProps {
  messages: Message[];
  isLoading?: boolean;
  showWorking?: boolean;
  onRegenerate?: (messageId: string) => void;
  inlinePanel?: ReactNode;
  className?: string;
}

const ChatMessagesList = ({
  messages,
  isLoading = false,
  showWorking = false,
  onRegenerate,
  inlinePanel,
  className,
}: ChatMessagesListProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [workingText, setWorkingText] = useState('Working on it...');
  const [isWorkingVisible, setIsWorkingVisible] = useState(false);

  const hasStreamingAssistant = messages.some(
    (m) => m.role === 'assistant' && m.isStreaming
  );

  // Only show the working bar after we've been waiting for a bit,
  // which aligns with slower agentic/DB/API operations.
  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    if (isLoading && showWorking && hasStreamingAssistant) {
      timer = setTimeout(() => setIsWorkingVisible(true), 1200);
    } else {
      setIsWorkingVisible(false);
    }
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [isLoading, showWorking, hasStreamingAssistant]);

  useEffect(() => {
    if (!isWorkingVisible) return;
    const phrases = [
      'Working on it...',
      'On it...',
      'Almost there...',
      'Fetching details...',
      'Crunching...',
    ];
    let idx = 0;
    setWorkingText(phrases[idx]);
    const interval = setInterval(() => {
      idx = (idx + 1) % phrases.length;
      setWorkingText(phrases[idx]);
    }, 1500);
    return () => clearInterval(interval);
  }, [isWorkingVisible]);

  // Check if scrolled to bottom
  const checkScrollPosition = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    const threshold = 100; // pixels from bottom
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    const atBottom = distanceFromBottom < threshold;

    setIsAtBottom(atBottom);
    setShowScrollButton(!atBottom && messages.length > 3);
  }, [messages.length]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (isAtBottom && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isAtBottom]);

  // Set up scroll listener
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('scroll', checkScrollPosition);
    return () => container.removeEventListener('scroll', checkScrollPosition);
  }, [checkScrollPosition]);

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Empty state with animated orb
  if (messages.length === 0 && !isLoading) {
    return (
      <div className={cn('flex-1 flex items-center justify-center p-8', className)}>
        <div className="flex flex-col items-center text-center max-w-md animate-fade-in">
          {/* Animated Orb */}
          <div className="mb-6">
            <AnimatedOrb
              size="lg"
              state="idle"
              enableBreathing={true}
              enableParticles={false}
            />
          </div>
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-5 h-5 text-accent-500" />
            <h3 className="text-xl font-semibold text-neutral-800 dark:text-neutral-200">
              Start a conversation
            </h3>
          </div>
          <p className="text-neutral-500 dark:text-neutral-400">
            Ask me anything about customer support. I&apos;m here to help!
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('relative flex-1 overflow-hidden', className)}>
      <div
        ref={containerRef}
        className="h-full overflow-y-auto scroll-smooth px-4 md:px-6"
      >
        <div className="max-w-3xl mx-auto py-6 space-y-4">
          {messages.map((message, index) => (
            <ChatMessage
              key={message.id}
              role={message.role as 'user' | 'assistant'}
              content={message.content}
              timestamp={message.timestamp}
              isStreaming={message.isStreaming}
              isLast={index === messages.length - 1}
              onRegenerate={
                index === messages.length - 1 && message.role === 'assistant' && onRegenerate
                  ? () => onRegenerate(message.id)
                  : undefined
              }
            />
          ))}

          {inlinePanel && (
            <div className="pt-2">
              {inlinePanel}
            </div>
          )}

          {/* Scroll anchor */}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Floating scroll to bottom button */}
      {showScrollButton && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 animate-slide-up">
          <button
            onClick={scrollToBottom}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-full',
              'bg-white/80 dark:bg-neutral-800/80',
              'backdrop-blur-xl',
              'border border-white/30 dark:border-white/10',
              'shadow-lg shadow-black/10',
              'text-sm font-medium text-neutral-700 dark:text-neutral-300',
              'hover:bg-white dark:hover:bg-neutral-700',
              'hover:scale-105 active:scale-95',
              'transition-all duration-300'
            )}
          >
            <ArrowDown className="w-4 h-4" />
            New messages
          </button>
        </div>
      )}

      {isWorkingVisible && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 animate-fade-in">
          <div className="flex items-center gap-3 px-4 py-2 rounded-full bg-white/80 dark:bg-neutral-800/80 backdrop-blur-xl border border-white/30 dark:border-white/10 shadow-lg">
            <div className="h-3 w-3 rounded-full bg-primary-500 animate-pulse" />
            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-200">
              {workingText}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export { ChatMessagesList };
