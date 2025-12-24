/**
 * Chat Input Component
 *
 * Modern floating text input with acrylic effect and send button.
 */

'use client';

import { useState, useRef, useCallback, KeyboardEvent, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Send, Loader2 } from 'lucide-react';
import { uiMsg } from '@/lib/ui-messages';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  isLoading?: boolean;
  className?: string;
}

const ChatInput = ({
  onSend,
  disabled = false,
  placeholder = uiMsg('chat.input.placeholder'),
  isLoading = false,
  className,
}: ChatInputProps) => {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (trimmed && !disabled && !isLoading) {
      onSend(trimmed);
      setValue('');
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        // restore focus after sending
        try {
          textareaRef.current.focus();
        } catch (e) {
          // ignore
        }
      }
    }
  }, [value, disabled, isLoading, onSend]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Send on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea
  const handleInput = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const maxHeight = 200; // Max height in pixels
      textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
    }
  };

  // Keep focus on the textarea after a reply finishes (when loading -> not loading)
  const prevLoadingRef = useRef(isLoading);
  useEffect(() => {
    if (prevLoadingRef.current && !isLoading) {
      // just finished loading a reply; restore focus
      if (textareaRef.current) textareaRef.current.focus();
    }
    prevLoadingRef.current = isLoading;
  }, [isLoading]);

  const canSend = value.trim().length > 0 && !disabled && !isLoading;

  return (
    <div
      className={cn(
        'relative flex items-end gap-3 p-3',
        'rounded-3xl',
        'bg-white/70 dark:bg-neutral-900/70',
        'backdrop-blur-xl',
        'border border-white/30 dark:border-white/10',
        'shadow-xl shadow-black/5 dark:shadow-black/20',
        'transition-all duration-300',
        'focus-within:shadow-2xl focus-within:border-primary-500/30',
        className
      )}
    >
      {/* Input area */}
      <div className="relative flex-1">
        <textarea
          ref={textareaRef}
          autoFocus
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder={placeholder}
          disabled={disabled || isLoading}
          rows={1}
          className={cn(
            'w-full px-2 py-2',
            'bg-transparent',
            'text-neutral-900 dark:text-neutral-100',
            'placeholder-neutral-400 dark:placeholder-neutral-500',
            'rounded-xl resize-none',
            'border-0 focus:outline-none',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'text-base leading-relaxed'
          )}
          aria-label={uiMsg('chat.input.aria')}
        />

        {/* Character count hint */}
        {value.length > 500 && (
          <span
            className={cn(
              'absolute right-2 bottom-2 text-xs',
              value.length > 2000 ? 'text-error-500' : 'text-neutral-400'
            )}
          >
            {value.length}/2000
          </span>
        )}
      </div>

      {/* Send button */}
      <button
        onClick={handleSend}
        disabled={!canSend}
        className={cn(
          'flex-shrink-0 p-3 rounded-full',
          'transition-all duration-300',
          canSend
            ? 'bg-gradient-to-r from-primary-500 to-accent-500 text-white shadow-lg shadow-primary-500/30 hover:shadow-xl hover:shadow-primary-500/40 hover:scale-105 active:scale-95'
            : 'bg-neutral-200 dark:bg-neutral-700 text-neutral-400 cursor-not-allowed'
        )}
        aria-label={uiMsg('chat.send.aria')}
      >
        {isLoading ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : (
          <Send className="w-5 h-5" />
        )}
      </button>
    </div>
  );
};

export { ChatInput };
