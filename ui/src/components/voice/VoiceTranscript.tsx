/**
 * Voice Transcript Component - Redesigned
 *
 * Live streaming transcript (input + output) with minimal styling.
 */

'use client';

import { memo, useMemo, useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import ReactMarkdown from 'react-markdown';
import type { VoiceTranscript as VoiceTranscriptType } from '@/types/api';

interface VoiceTranscriptProps {
  transcripts: VoiceTranscriptType[];
  className?: string;
}

const VoiceTranscript = memo(function VoiceTranscript({
  transcripts,
  className,
}: VoiceTranscriptProps) {
  const [displayedAssistantText, setDisplayedAssistantText] = useState('');
  const [displayedUserText, setDisplayedUserText] = useState('');
  
  if (transcripts.length === 0) {
    return null;
  }

  const { latestUser, latestAssistant } = useMemo(() => {
    let latestUser: VoiceTranscriptType | undefined;
    let latestAssistant: VoiceTranscriptType | undefined;

    for (let i = transcripts.length - 1; i >= 0; i--) {
      const t = transcripts[i];
      if (!latestAssistant && t.role === 'assistant') latestAssistant = t;
      if (!latestUser && t.role === 'user') latestUser = t;
      if (latestAssistant && latestUser) break;
    }

    return { latestUser, latestAssistant };
  }, [transcripts]);

  // Streaming effect for user text (STT) - character by character
  useEffect(() => {
    if (!latestUser?.text) {
      setDisplayedUserText('');
      return;
    }

    const targetText = latestUser.text;
    
    // If we already have this text displayed, don't re-stream
    if (displayedUserText === targetText) {
      return;
    }
    
    // If the new text starts with what we have, continue from there
    const startIndex = targetText.startsWith(displayedUserText) 
      ? displayedUserText.length 
      : 0;
    
    if (startIndex === 0) {
      setDisplayedUserText('');
    }
    
    let currentIndex = startIndex;
    
    const interval = setInterval(() => {
      if (currentIndex < targetText.length) {
        setDisplayedUserText(targetText.slice(0, currentIndex + 1));
        currentIndex++;
      } else {
        clearInterval(interval);
      }
    }, 50); // 50ms per character for user speech

    return () => clearInterval(interval);
  }, [latestUser?.text, latestUser?.id]);

  // Streaming effect for assistant text - always stream, even when final
  useEffect(() => {
    if (!latestAssistant?.text) {
      setDisplayedAssistantText('');
      return;
    }

    const targetText = latestAssistant.text;
    
    // If we already have this text displayed, don't re-stream
    if (displayedAssistantText === targetText) {
      return;
    }
    
    // If the new text starts with what we have, continue from there
    const startIndex = targetText.startsWith(displayedAssistantText) 
      ? displayedAssistantText.length 
      : 0;
    
    if (startIndex === 0) {
      setDisplayedAssistantText('');
    }
    
    let currentIndex = startIndex;
    
    const interval = setInterval(() => {
      if (currentIndex < targetText.length) {
        setDisplayedAssistantText(targetText.slice(0, currentIndex + 1));
        currentIndex++;
      } else {
        clearInterval(interval);
      }
    }, 50); // 50ms per character to match voice pace

    return () => clearInterval(interval);
  }, [latestAssistant?.text, latestAssistant?.id]);

  return (
    <div 
      className={cn(
        'w-full max-w-2xl mx-auto max-h-[350px] overflow-y-auto',
        'scrollbar-thin scrollbar-thumb-neutral-300 dark:scrollbar-thumb-neutral-600',
        className
      )}
    >
      <div className="flex flex-col gap-3 text-center">
        {latestUser?.text && (
          <div className="px-2">
            <div className="text-[11px] uppercase tracking-[0.22em] text-neutral-500 dark:text-neutral-400">
              You
            </div>
            <div className="text-base md:text-lg leading-relaxed text-neutral-800 dark:text-neutral-100">
              {displayedUserText || latestUser.text}
            </div>
          </div>
        )}

        {latestAssistant?.text && (
          <div className="px-2">
            <div className="text-[11px] uppercase tracking-[0.22em] text-neutral-500 dark:text-neutral-400">
              Rashmi
            </div>
            <div className="text-base md:text-lg leading-relaxed text-neutral-800 dark:text-neutral-100 prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown>{displayedAssistantText || latestAssistant.text}</ReactMarkdown>
              {!latestAssistant.isFinal && displayedAssistantText.length < latestAssistant.text.length && (
                <span className="inline-block w-2 h-5 ml-1 bg-current animate-pulse rounded-sm" />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
});

interface VoiceTranscriptItemProps {
  role: 'user' | 'assistant';
  text: string;
  isFinal?: boolean;
  opacity?: number;
  isHighlighted?: boolean;
}

const VoiceTranscriptItem = memo(function VoiceTranscriptItem({
  role,
  text,
  isFinal = true,
  opacity = 1,
  isHighlighted = false,
}: VoiceTranscriptItemProps) {
  return (
    <div style={{ opacity }} className={cn('text-center', isHighlighted && 'scale-[1.01]')}>
      <div className="text-[11px] uppercase tracking-[0.22em] text-white/55">
        {role}
      </div>
      <div className={cn('text-sm text-white/85', !isFinal && 'opacity-80')}>{text}</div>
    </div>
  );
});

export { VoiceTranscript, VoiceTranscriptItem };
