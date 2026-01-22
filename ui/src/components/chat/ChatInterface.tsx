/**
 * Chat Interface Component
 *
 * Modern chat interface with floating elements and acrylic effects.
 */

'use client';

import { memo, type ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { ChatMessagesList } from './ChatMessagesList';
import { ChatInput } from './ChatInput';
import type { Message } from '@/types/api';

interface ChatInterfaceProps {
  messages: Message[];
  isLoading?: boolean;
  showWorking?: boolean;
  agenticPanel?: ReactNode;
  onSend: (content: string) => void;
  onRegenerate?: (messageId: string) => void;
  activeSessionId: string | null;
  className?: string;
}

const ChatInterface = memo(function ChatInterface({
  messages,
  isLoading = false,
  showWorking = false,
  agenticPanel,
  onSend,
  onRegenerate,
  activeSessionId,
  className,
}: ChatInterfaceProps) {
  return (
    <div className={cn('flex-1 flex flex-col min-h-0', className)}>
      {/* Messages area */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <ChatMessagesList
          messages={messages}
          isLoading={isLoading}
          showWorking={showWorking}
          onRegenerate={onRegenerate}
          className="h-full"
        />
      </div>

      {agenticPanel && (
        <div className="px-4 md:px-6 pb-2">
          <div className="max-w-3xl mx-auto flex justify-center">
            <div
              className={cn(
                'w-fit max-w-[75%] px-4 py-3',
                'backdrop-blur-lg',
                'shadow-lg',
                'rounded-3xl rounded-bl-lg',
                'bg-white/70 dark:bg-neutral-800/70',
                'border border-white/30 dark:border-white/10',
                'text-neutral-900 dark:text-neutral-100'
              )}
            >
              {agenticPanel}
            </div>
          </div>
        </div>
      )}

      {/* Floating input at bottom */}
      <div className="p-4 md:p-6">
        <div className="max-w-3xl mx-auto">
          <ChatInput
            onSend={onSend}
            isLoading={isLoading}
            disabled={isLoading}
            placeholder={
              activeSessionId
                ? 'Type your message...'
                : 'Start a new conversation...'
            }
          />
        </div>
      </div>
    </div>
  );
});

export { ChatInterface };
