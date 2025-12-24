/**
 * Chat Message Component
 *
 * Modern floating chat messages with acrylic effects,
 * markdown support, and smooth animations.
 */

'use client';

import { memo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import { User, Copy, Check, RotateCcw, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  isStreaming?: boolean;
  isLast?: boolean;
  sources?: Array<{ source: string; relevance?: number }>;
  onCopy?: () => void;
  onRegenerate?: () => void;
  className?: string;
}

/**
 * Typing indicator with bouncing dots
 */
const TypingIndicator = () => (
  <div className="flex items-center gap-1.5 py-1">
    <span 
      className="w-2 h-2 bg-accent-400 rounded-full animate-bounce"
      style={{ animationDelay: '0ms', animationDuration: '600ms' }}
    />
    <span 
      className="w-2 h-2 bg-accent-400 rounded-full animate-bounce"
      style={{ animationDelay: '150ms', animationDuration: '600ms' }}
    />
    <span 
      className="w-2 h-2 bg-accent-400 rounded-full animate-bounce"
      style={{ animationDelay: '300ms', animationDuration: '600ms' }}
    />
  </div>
);

const ChatMessage = memo(function ChatMessage({
  role,
  content,
  timestamp,
  isStreaming = false,
  isLast: _isLast = false,
  sources,
  onCopy,
  onRegenerate,
  className,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const [showSources, setShowSources] = useState(false);

  const isUser = role === 'user';

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    onCopy?.();
  };

  return (
    <div
      className={cn(
        'group flex gap-3 chat-bubble',
        isUser ? 'flex-row-reverse' : 'flex-row',
        'will-change-transform',
        className
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex-shrink-0 w-9 h-9 rounded-2xl flex items-center justify-center',
          'shadow-md',
          'transition-transform duration-200 group-hover:scale-105',
          isUser
            ? 'bg-gradient-to-br from-primary-400 to-primary-600 text-white'
            : 'bg-gradient-to-br from-accent-400 to-accent-600 text-white'
        )}
      >
        {isUser ? <User className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
      </div>

      {/* Content */}
      <div
        className={cn(
          'flex flex-col max-w-[85%] md:max-w-[75%]',
          isUser ? 'items-end' : 'items-start'
        )}
      >
        {/* Message bubble */}
        <div
          className={cn(
            'relative px-4 py-3',
            'backdrop-blur-lg',
            'shadow-lg',
            'transition-all duration-300 ease-out',
            'hover:shadow-xl',
            'hover:-translate-y-[1px]',
            'motion-reduce:transform-none',
            isUser
              ? cn(
                  'rounded-3xl rounded-br-lg',
                  'bg-gradient-to-br from-primary-500 to-primary-600',
                  'text-white'
                )
              : cn(
                  'rounded-3xl rounded-bl-lg',
                  'bg-white/70 dark:bg-neutral-800/70',
                  'border border-white/30 dark:border-white/10',
                  'text-neutral-900 dark:text-neutral-100'
                )
          )}
        >
          {/* Markdown content or typing indicator */}
          {isStreaming && !content ? (
            <TypingIndicator />
          ) : (
            <div
              className={cn(
                'prose prose-sm max-w-none',
                isUser
                  ? 'prose-invert'
                  : 'dark:prose-invert',
                // Code block styling
                '[&_pre]:bg-neutral-900 [&_pre]:text-neutral-100 [&_pre]:rounded-xl [&_pre]:p-3 [&_pre]:overflow-x-auto',
                '[&_code]:bg-neutral-200/50 [&_code]:dark:bg-neutral-700/50 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded-lg [&_code]:text-sm',
                '[&_pre_code]:bg-transparent [&_pre_code]:p-0',
                // Link styling
                isUser ? '[&_a]:text-primary-200 [&_a]:underline' : '[&_a]:text-primary-500 dark:[&_a]:text-primary-400 [&_a]:underline'
              )}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content}
              </ReactMarkdown>
              {isStreaming && content && (
                <span className="inline-block w-2 h-5 ml-1 bg-current animate-pulse rounded-sm" />
              )}
            </div>
          )}
        </div>

        {/* Sources */}
        {sources && sources.length > 0 && !isUser && (
          <div className="mt-2 w-full">
            <button
              onClick={() => setShowSources(!showSources)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-full',
                'text-xs text-neutral-500 dark:text-neutral-400',
                'bg-white/50 dark:bg-neutral-800/50',
                'hover:bg-white/80 dark:hover:bg-neutral-700/80',
                'transition-all duration-200'
              )}
            >
              {showSources ? (
                <ChevronUp className="w-3 h-3" />
              ) : (
                <ChevronDown className="w-3 h-3" />
              )}
              {sources.length} source{sources.length !== 1 ? 's' : ''}
            </button>

            {showSources && (
              <div className="mt-2 space-y-1 animate-fade-in">
                {sources.map((source, idx) => (
                  <div
                    key={idx}
                    className={cn(
                      'text-xs px-3 py-2 rounded-xl',
                      'bg-white/50 dark:bg-neutral-800/50',
                      'text-neutral-600 dark:text-neutral-400',
                      'flex items-center gap-2'
                    )}
                  >
                    <span className="truncate flex-1">{source.source}</span>
                    {source.relevance && (
                      <Badge variant="default" size="sm">
                        {(source.relevance * 100).toFixed(0)}%
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Metadata and actions */}
        <div
          className={cn(
            'flex items-center gap-2 mt-2 text-xs text-neutral-400',
            isUser ? 'flex-row-reverse' : 'flex-row'
          )}
        >
          {timestamp && (
            <time dateTime={timestamp} className="opacity-60">
              {new Date(timestamp).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </time>
          )}

          {/* Actions - only show on hover for assistant messages */}
          {!isUser && !isStreaming && (
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              <button
                onClick={handleCopy}
                className={cn(
                  'p-1.5 rounded-lg',
                  'hover:bg-neutral-100/50 dark:hover:bg-neutral-800/50',
                  'transition-colors duration-200'
                )}
                aria-label={copied ? 'Copied' : 'Copy message'}
              >
                {copied ? (
                  <Check className="w-3.5 h-3.5 text-green-500" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
              </button>
              {onRegenerate && (
                <button
                  onClick={onRegenerate}
                  className={cn(
                    'p-1.5 rounded-lg',
                    'hover:bg-neutral-100/50 dark:hover:bg-neutral-800/50',
                    'transition-colors duration-200'
                  )}
                  aria-label="Retry"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

export { ChatMessage };
