/**
 * Chat Interface Component
 *
 * Modern chat interface with floating elements and acrylic effects.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { ChatMessagesList } from './ChatMessagesList';
import { ChatInput } from './ChatInput';
import type { Message } from '@/types/api';

interface ChatInterfaceProps {
  messages: Message[];
  isLoading?: boolean;
  onSend: (content: string) => void;
  onRegenerate?: (messageId: string) => void;
  activeSessionId: string | null;
  className?: string;
}

const ChatInterface = memo(function ChatInterface({
  messages,
  isLoading = false,
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
          onRegenerate={onRegenerate}
          className="h-full"
        />
      </div>

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
