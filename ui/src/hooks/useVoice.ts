/**
 * useVoice Hook
 *
 * Manages voice chat state, speech recognition, and synthesis.
 */

'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import type { VoiceTranscript, VoiceState } from '@/types/api';

// Web Speech API types
interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  length: number;
  isFinal: boolean;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message?: string;
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognition;
    webkitSpeechRecognition: new () => SpeechRecognition;
  }
}

interface UseVoiceOptions {
  onTranscript?: (text: string, isFinal: boolean) => void;
  onResponse?: (text: string) => void;
  onError?: (error: Error) => void;
  language?: string;
}

interface UseVoiceReturn {
  state: VoiceState;
  transcripts: VoiceTranscript[];
  isSupported: boolean;
  start: () => Promise<void>;
  stop: () => void;
  speak: (text: string) => Promise<void>;
  clearTranscripts: () => void;
}

export function useVoice({
  onTranscript,
  onResponse,
  onError,
  language = 'en-US',
}: UseVoiceOptions = {}): UseVoiceReturn {
  const [state, setState] = useState<VoiceState>('idle');
  const [transcripts, setTranscripts] = useState<VoiceTranscript[]>([]);
  const [isSupported, setIsSupported] = useState(false);

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const synthesisRef = useRef<SpeechSynthesisUtterance | null>(null);

  // Check for browser support
  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    setIsSupported(!!SpeechRecognition && !!window.speechSynthesis);
  }, []);

  // Initialize speech recognition
  const initRecognition = useCallback(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      onError?.(new Error('Speech recognition not supported'));
      return null;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = language;

    recognition.onresult = (event) => {
      const lastResult = event.results[event.results.length - 1];
      const text = lastResult[0].transcript;
      const isFinal = lastResult.isFinal;

      // Update or add transcript
      setTranscripts((prev) => {
        const lastTranscript = prev[prev.length - 1];
        if (lastTranscript && !lastTranscript.isFinal && lastTranscript.role === 'user') {
          // Update existing interim transcript
          return prev.map((t, i) =>
            i === prev.length - 1
              ? { ...t, text, isFinal }
              : t
          );
        } else {
          // Add new transcript
          return [
            ...prev,
            {
              id: uuidv4(),
              role: 'user',
              text,
              timestamp: new Date().toISOString(),
              isFinal,
            },
          ];
        }
      });

      onTranscript?.(text, isFinal);
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      if (event.error !== 'no-speech') {
        onError?.(new Error(`Speech recognition error: ${event.error}`));
      }
      setState('idle');
    };

    recognition.onend = () => {
      setState('idle');
    };

    return recognition;
  }, [language, onTranscript, onError]);

  // Start listening
  const start = useCallback(async () => {
    if (state !== 'idle') return;

    try {
      // Request microphone permission
      await navigator.mediaDevices.getUserMedia({ audio: true });

      const recognition = initRecognition();
      if (!recognition) return;

      recognitionRef.current = recognition;
      recognition.start();
      setState('listening');
    } catch (err) {
      const error =
        err instanceof Error
          ? err
          : new Error('Failed to access microphone');
      onError?.(error);
    }
  }, [state, initRecognition, onError]);

  // Stop listening
  const stop = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setState('idle');
  }, []);

  // Speak text using TTS
  const speak = useCallback(
    async (text: string) => {
      if (!window.speechSynthesis) {
        onError?.(new Error('Speech synthesis not supported'));
        return;
      }

      return new Promise<void>((resolve, reject) => {
        // Cancel any ongoing speech
        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = language;
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        // Add assistant transcript
        setTranscripts((prev) => [
          ...prev,
          {
            id: uuidv4(),
            role: 'assistant',
            text,
            timestamp: new Date().toISOString(),
            isFinal: true,
          },
        ]);

        utterance.onstart = () => {
          setState('speaking');
        };

        utterance.onend = () => {
          setState('idle');
          onResponse?.(text);
          resolve();
        };

        utterance.onerror = (event) => {
          setState('idle');
          reject(new Error(`Speech synthesis error: ${event.error}`));
        };

        synthesisRef.current = utterance;
        window.speechSynthesis.speak(utterance);
      });
    },
    [language, onResponse, onError]
  );

  // Clear transcripts
  const clearTranscripts = useCallback(() => {
    setTranscripts([]);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      window.speechSynthesis?.cancel();
    };
  }, []);

  return {
    state,
    transcripts,
    isSupported,
    start,
    stop,
    speak,
    clearTranscripts,
  };
}
