/**
 * Voice Chat Page
 *
 * Voice-based interaction with the AI assistant.
 * Uses Web Speech API for STT and direct audio playback from backend TTS.
 * Wrapped with VoiceErrorBoundary for graceful error handling.
 */

'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import { AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { VoiceOrb, VoiceOrbState } from '@/components/voice/VoiceOrb';
import { VoiceTranscript } from '@/components/voice/VoiceTranscript';
import { VoiceControls } from '@/components/voice/VoiceControls';
import { VoiceErrorBoundary } from '@/components/voice/VoiceErrorBoundary';
import { v4 as uuidv4 } from 'uuid';
import { apiClient } from '@/lib/api-client';
import { getFriendlyError } from '@/lib/errors';
import type { VoiceTranscript as VoiceTranscriptType, VoiceState } from '@/types/api';

// Inner component that contains the actual voice functionality
function VoicePageContent() {
  const [mode, setMode] = useState<'push-to-talk' | 'continuous'>('continuous');
  const [isProcessing, setIsProcessing] = useState(false);
  const [state, setState] = useState<VoiceState>('idle');
  const [transcripts, setTranscripts] = useState<VoiceTranscriptType[]>([]);
  const [isSupported, setIsSupported] = useState(false);

  // Stable server-side conversation context for this voice session
  const chatSessionIdRef = useRef<string>(uuidv4());
  
  // Refs for speech recognition
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const lastTranscriptRef = useRef<string>('');
  const processingRef = useRef<boolean>(false);
  const isSpeakingRef = useRef<boolean>(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const audioCancelledRef = useRef<boolean>(false); // Track intentional audio stop (barge-in)

  // Recognition suspension during TTS (prevents echo pickup)
  const suspendRecognitionRef = useRef<boolean>(false);
  // Drop STT results until this timestamp (tail-echo / buffered results)
  const ignoreRecognitionUntilRef = useRef<number>(0);

  // Mic-level barge-in detection (VAD) for continuous mode
  const micStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const vadIntervalRef = useRef<number | null>(null);
  const vadConsecutiveRef = useRef<number>(0);

  // Abort controllers for in-flight work
  const ttsAbortRef = useRef<AbortController | null>(null);
  const queryAbortRef = useRef<AbortController | null>(null);
  
  // Store the last assistant response to filter from STT
  const lastAssistantTextRef = useRef<string>('');
  const assistantUtterancesRef = useRef<string[]>([]);
  const ttsStartTimeRef = useRef<number>(0); // When TTS started playing
  const ttsEndTimeRef = useRef<number>(0); // When TTS finished playing

  // Refs for current state/mode to avoid stale closures in callbacks
  const stateRef = useRef<VoiceState>('idle' as VoiceState);
  const modeRef = useRef<'push-to-talk' | 'continuous'>('continuous');
  const stoppedRef = useRef<boolean>(false); // Track explicit stop to prevent restart
  
  // Ref for processUserInput to avoid circular dependency
  const processUserInputRef = useRef<((text: string) => Promise<void>) | null>(null);
  
  // Update refs when state changes
  useEffect(() => {
    stateRef.current = state;
  }, [state]);
  
  useEffect(() => {
    modeRef.current = mode;
    
    // If we're actively listening, restart recognition to pick up new mode behavior
    if (recognitionRef.current && state !== 'idle') {
      recognitionRef.current.stop();
      // It will auto-restart via the onend handler with the new mode
    }
  }, [mode, state]);

  // Cleanup on unmount - ensure all resources are freed
  useEffect(() => {
    return () => {
      stoppedRef.current = true;
      audioCancelledRef.current = true;

      // Stop VAD and release mic stream (if we acquired it)
      try {
        if (vadIntervalRef.current) {
          window.clearInterval(vadIntervalRef.current);
          vadIntervalRef.current = null;
        }
      } catch {
        // Ignore
      }
      try {
        if (audioContextRef.current) {
          audioContextRef.current.close();
          audioContextRef.current = null;
        }
      } catch {
        // Ignore
      }
      try {
        if (micStreamRef.current) {
          for (const track of micStreamRef.current.getTracks()) {
            track.stop();
          }
          micStreamRef.current = null;
        }
      } catch {
        // Ignore
      }

      try {
        queryAbortRef.current?.abort();
      } catch {
        // Ignore
      } finally {
        queryAbortRef.current = null;
      }

      try {
        ttsAbortRef.current?.abort();
      } catch {
        // Ignore
      } finally {
        ttsAbortRef.current = null;
      }
      
      try {
        if (recognitionRef.current) {
          recognitionRef.current.onend = null;
          recognitionRef.current.onerror = null;
          recognitionRef.current.onresult = null;
          recognitionRef.current.stop();
          recognitionRef.current = null;
        }
      } catch {
        // Ignore
      }
      
      try {
        if (audioRef.current) {
          audioRef.current.onended = null;
          audioRef.current.onerror = null;
          audioRef.current.pause();
          audioRef.current.src = '';
          audioRef.current = null;
        }
      } catch {
        // Ignore
      }

      try {
        if (audioUrlRef.current) {
          URL.revokeObjectURL(audioUrlRef.current);
          audioUrlRef.current = null;
        }
      } catch {
        // Ignore
      }
    };
  }, []);

  // Check browser support
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    setIsSupported(!!SpeechRecognition);
  }, []);

  // Helper to add transcript
  const addTranscript = useCallback((role: 'user' | 'assistant', text: string, isFinal: boolean = true) => {
    setTranscripts(prev => {
      // If updating an interim user transcript
      if (role === 'user' && !isFinal) {
        const lastTranscript = prev[prev.length - 1];
        if (lastTranscript && !lastTranscript.isFinal && lastTranscript.role === 'user') {
          return prev.map((t, i) => 
            i === prev.length - 1 ? { ...t, text, isFinal } : t
          );
        }
      }
      return [...prev, {
        id: uuidv4(),
        role,
        text,
        timestamp: new Date().toISOString(),
        isFinal,
      }];
    });
  }, []);

  // Check if text is similar to what we just spoke (to filter echo)
  const isSimilarToLastResponse = useCallback((text: string): boolean => {
    const now = Date.now();
    const echoWindowMs = 6000;

    // Only apply echo filtering shortly after TTS ended (or while it is/was playing).
    const ttsEndedAt = ttsEndTimeRef.current;
    const ttsStartedAt = ttsStartTimeRef.current;
    const withinWindow =
      (ttsEndedAt > 0 && now - ttsEndedAt <= echoWindowMs) ||
      (ttsEndedAt === 0 && ttsStartedAt > 0 && now - ttsStartedAt <= echoWindowMs + 2000);
    if (!withinWindow) return false;

    const normalizedText = text.toLowerCase().trim();
    if (!normalizedText) return false;

    const candidates = [
      lastAssistantTextRef.current,
      ...assistantUtterancesRef.current,
    ]
      .map((s) => s.toLowerCase().trim())
      .filter(Boolean);

    for (const candidate of candidates) {
      // Substring match (common when the speaker leaks into the mic)
      if (
        (candidate.includes(normalizedText) ||
          normalizedText.includes(candidate.slice(0, 24))) &&
        normalizedText.length > 3
      ) {
        return true;
      }

      // Word overlap heuristic
      const inputWords = normalizedText.split(/\s+/).filter((w) => w.length > 2);
      const responseWords = new Set(candidate.split(/\s+/).filter((w) => w.length > 2));
      if (inputWords.length < 2 || responseWords.size < 2) continue;

      let matchCount = 0;
      for (const word of inputWords) {
        if (responseWords.has(word)) matchCount++;
      }
      if ((matchCount / inputWords.length) > 0.5) return true;
    }

    return false;
  }, []);

  const assistantEchoOverlapRatio = useCallback((text: string): number => {
    const normalizedText = text.toLowerCase().trim();
    if (!normalizedText) return 0;

    const inputWords = normalizedText.split(/\s+/).filter((w) => w.length > 2);
    if (inputWords.length < 2) return 0;

    const candidates = [
      lastAssistantTextRef.current,
      ...assistantUtterancesRef.current,
    ]
      .map((s) => s.toLowerCase().trim())
      .filter(Boolean);

    let bestRatio = 0;
    for (const candidate of candidates) {
      const responseWords = new Set(candidate.split(/\s+/).filter((w) => w.length > 2));
      if (responseWords.size < 2) continue;

      let matchCount = 0;
      for (const word of inputWords) {
        if (responseWords.has(word)) matchCount++;
      }
      const ratio = matchCount / inputWords.length;
      if (ratio > bestRatio) bestRatio = ratio;
      if (bestRatio >= 0.9) return bestRatio;
    }

    return bestRatio;
  }, []);

  const stripAssistantEchoFromText = useCallback((text: string): string => {
    const lower = text.toLowerCase();
    const normalized = lower.trim();
    if (!normalized) return '';

    const candidates = [
      lastAssistantTextRef.current,
      ...assistantUtterancesRef.current,
    ]
      .map((s) => s.toLowerCase().trim())
      .filter(Boolean);

    for (const candidate of candidates) {
      // If the entire recognized text is contained in what we just spoke, it's pure echo.
      if (normalized.length > 10 && candidate.includes(normalized)) {
        return '';
      }

      // Strip a shared prefix (common when TTS bleeds into the first STT chunk).
      const max = Math.min(normalized.length, candidate.length);
      let prefixLen = 0;
      while (prefixLen < max && normalized[prefixLen] === candidate[prefixLen]) prefixLen++;
      if (prefixLen >= 18) {
        return text.slice(text.length - (lower.length - prefixLen)).trimStart();
      }

      // Strip a long initial segment that matches the assistant start.
      const key = candidate.slice(0, 48);
      if (key.length >= 24) {
        const idx = normalized.indexOf(key);
        if (idx >= 0 && idx <= 5) {
          const cut = idx + key.length;
          return text.slice(text.length - (lower.length - cut)).trimStart();
        }
      }
    }

    return text;
  }, []);

  const stopBargeInMonitor = useCallback(() => {
    try {
      if (vadIntervalRef.current) {
        window.clearInterval(vadIntervalRef.current);
        vadIntervalRef.current = null;
      }
    } catch {
      // Ignore
    }
    vadConsecutiveRef.current = 0;
  }, []);

  const startBargeInMonitor = useCallback(async () => {
    // Only needed for continuous mode
    if (modeRef.current !== 'continuous') return;

    // Ensure only one monitor
    stopBargeInMonitor();

    try {
      // Request mic stream with common AEC flags (helps the monitor, even though SpeechRecognition is separate)
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      micStreamRef.current = stream;

      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AudioCtx();
      audioContextRef.current = ctx;

      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      analyser.smoothingTimeConstant = 0.8;
      analyserRef.current = analyser;
      source.connect(analyser);

      const data = new Uint8Array(analyser.fftSize);

      // Poll mic level: when user speaks during TTS, interrupt TTS.
      // Thresholds chosen to be conservative; avoids false triggers on silence.
      const threshold = 0.06;
      const requiredConsecutive = 3;
      vadIntervalRef.current = window.setInterval(() => {
        if (!analyserRef.current) return;
        if (!isSpeakingRef.current) {
          vadConsecutiveRef.current = 0;
          return;
        }

        analyserRef.current.getByteTimeDomainData(data);
        let sumSquares = 0;
        for (let i = 0; i < data.length; i++) {
          const v = (data[i] - 128) / 128;
          sumSquares += v * v;
        }
        const rms = Math.sqrt(sumSquares / data.length);

        if (rms > threshold) {
          vadConsecutiveRef.current += 1;
        } else {
          vadConsecutiveRef.current = 0;
        }

        if (vadConsecutiveRef.current >= requiredConsecutive) {
          vadConsecutiveRef.current = 0;

          // Barge-in: stop current TTS immediately
          if (audioRef.current) {
            audioCancelledRef.current = true;
            try {
              audioRef.current.pause();
              audioRef.current.src = '';
            } catch {
              // Ignore
            }
          }
          isSpeakingRef.current = false;
          ttsEndTimeRef.current = Date.now();

          stopBargeInMonitor();

          // Resume recognition after barge-in
          if (!stoppedRef.current && (stateRef.current as VoiceState) !== 'idle') {
            suspendRecognitionRef.current = false;
            // Drop buffered tail-echo right after barge-in
            ignoreRecognitionUntilRef.current = Date.now() + 900;
            window.setTimeout(() => {
              if (!stoppedRef.current && recognitionRef.current) {
                try {
                  recognitionRef.current.start();
                } catch {
                  // Ignore
                }
              }
            }, 150);
          }
        }
      }, 80);
    } catch {
      // If mic permission fails here, we still prevent echo by suspending recognition during TTS.
      stopBargeInMonitor();
    }
  }, [stopBargeInMonitor]);

  // Initialize speech recognition
  const initRecognition = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return null;

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      if (stoppedRef.current || (stateRef.current as VoiceState) === 'idle') return;

      const now = Date.now();

      // Guard against any buffered results that arrive after an intentional stop.
      if (suspendRecognitionRef.current) return;

      const lastResult = event.results[event.results.length - 1];
      let text = lastResult[0].transcript.trim();
      const isFinal = lastResult.isFinal;

      // During the tail-echo window (post TTS / barge-in), sanitize assistant leakage.
      // This aims to keep user barge-in speech while stripping the overlapped TTS.
      if (ignoreRecognitionUntilRef.current && now < ignoreRecognitionUntilRef.current) {
        const overlap = assistantEchoOverlapRatio(text);
        if (overlap >= 0.85) return; // pure assistant echo
        if (overlap >= 0.35) {
          const cleaned = stripAssistantEchoFromText(text);
          if (!cleaned) return;
          text = cleaned;
        }
      }

      // Use refs for current values to avoid stale closures
      const currentMode = modeRef.current;

      // Push-to-talk is strictly turn-based: only accept results while we're in listening state
      // and not already processing a request.
      if (
        currentMode === 'push-to-talk' &&
        (((stateRef.current as VoiceState) !== 'listening') || processingRef.current)
      ) {
        return;
      }

      // While speaking we suspend recognition in continuous mode, so this should be rare.
      // Still guard against accidental echo pickup.
      if (isSpeakingRef.current) return;

      // Skip echo after TTS finished (within window)
      if (isSimilarToLastResponse(text)) {
        return;
      }

      // Update transcript display
      addTranscript('user', text, isFinal);

      // Process when we get a final result
      if (isFinal && !processingRef.current && text.trim()) {
        lastTranscriptRef.current = text;

        // If we are still within the tail window and the final transcript is echo-dominant,
        // don't send it to the backend (prevents self-trigger loops).
        if (
          ignoreRecognitionUntilRef.current &&
          now < ignoreRecognitionUntilRef.current &&
          assistantEchoOverlapRatio(text) >= 0.6
        ) {
          return;
        }
        
        // In push-to-talk mode (voice-chat), stop recognition after final result
        // In continuous mode (realtime), keep listening
        if (currentMode === 'push-to-talk') {
          // Prevent onend from auto-restarting during thinking/speaking
          suspendRecognitionRef.current = true;
          recognition.stop();
        }
        
        // Call via ref to avoid circular dependency
        processUserInputRef.current?.(text);
      }
    };

    recognition.onerror = (event) => {
      // Ignore common non-critical errors
      if (event.error === 'no-speech' || event.error === 'aborted') {
        return;
      }
      console.error('Speech recognition error:', event.error);
      toast.error('Speech recognition error', { description: event.error });
    };

    recognition.onend = () => {
      // Use refs to get current values - state can change between onend calls
      const currentState = stateRef.current;
      const wasStopped = stoppedRef.current;

      // If recognition is intentionally suspended (e.g., during TTS), do not restart.
      if (suspendRecognitionRef.current) return;

      // Push-to-talk: never auto-restart on end (we explicitly restart after finishing a turn)
      if (modeRef.current === 'push-to-talk') return;
      
      // Only restart if:
      // - This recognition instance is still the active one
      // - Not explicitly stopped
      // - Not idle
      if (recognitionRef.current === recognition && !wasStopped && (currentState as VoiceState) !== 'idle') {
        try {
          recognition.start();
        } catch {
          // Ignore - already started
        }
      }
    };

    return recognition;
  }, [addTranscript, assistantEchoOverlapRatio, isSimilarToLastResponse, stripAssistantEchoFromText]);

  // Play TTS audio from backend
  const playTTS = useCallback(async (text: string): Promise<void> => {
    if (stoppedRef.current || (stateRef.current as VoiceState) === 'idle') return;

    // Reset cancelled flag and set TTS start time
    audioCancelledRef.current = false;
    ttsStartTimeRef.current = Date.now();
    ttsEndTimeRef.current = 0; // Mark as currently playing

    // Abort any previous TTS fetch
    try {
      ttsAbortRef.current?.abort();
    } catch {
      // Ignore
    }
    const controller = new AbortController();
    ttsAbortRef.current = controller;
    
    return new Promise(async (resolve, reject) => {
      try {
        if (stoppedRef.current || (stateRef.current as VoiceState) === 'idle') {
          resolve();
          return;
        }

        // Stop any currently playing audio
        if (audioRef.current) {
          audioRef.current.pause();
          audioRef.current.src = '';
        }

        if (audioUrlRef.current) {
          try {
            URL.revokeObjectURL(audioUrlRef.current);
          } catch {
            // Ignore
          }
          audioUrlRef.current = null;
        }

        // Fetch TTS audio from backend
        const response = await fetch('/api/tts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text }),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error('TTS request failed');
        }

        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        audioUrlRef.current = audioUrl;
        
        const audio = new Audio(audioUrl);
        audioRef.current = audio;

        // Continuous mode: suspend SpeechRecognition during TTS to prevent echo,
        // but enable barge-in via mic-level VAD.
        if (modeRef.current === 'continuous' && recognitionRef.current) {
          suspendRecognitionRef.current = true;
          try {
            recognitionRef.current.stop();
          } catch {
            // Ignore
          }
          await startBargeInMonitor();
        }
        
        audio.onended = () => {
          try {
            URL.revokeObjectURL(audioUrl);
          } catch {
            // Ignore
          }
          if (audioUrlRef.current === audioUrl) audioUrlRef.current = null;
          isSpeakingRef.current = false;
          ttsEndTimeRef.current = Date.now(); // Mark when TTS ended
          // Drop buffered tail-echo right after TTS
          ignoreRecognitionUntilRef.current = Date.now() + 900;

          stopBargeInMonitor();
          suspendRecognitionRef.current = false;
          // Restart recognition after a short delay to avoid catching tail echo
          if (
            modeRef.current === 'continuous' &&
            !stoppedRef.current &&
            (stateRef.current as VoiceState) !== 'idle' &&
            recognitionRef.current
          ) {
            window.setTimeout(() => {
              if (!stoppedRef.current && recognitionRef.current) {
                try {
                  recognitionRef.current.start();
                } catch {
                  // Ignore
                }
              }
            }, 150);
          }
          resolve();
        };
        
        // Handle pause event (barge-in) - resolve instead of reject
        audio.onpause = () => {
          if (audioCancelledRef.current) {
            try {
              URL.revokeObjectURL(audioUrl);
            } catch {
              // Ignore
            }
            if (audioUrlRef.current === audioUrl) audioUrlRef.current = null;
            isSpeakingRef.current = false;
            ttsEndTimeRef.current = Date.now(); // Mark when TTS was interrupted
            audioCancelledRef.current = false;
            ignoreRecognitionUntilRef.current = Date.now() + 900;

            stopBargeInMonitor();
            suspendRecognitionRef.current = false;
            resolve(); // Resolve gracefully on barge-in
          }
        };
        
        audio.onerror = () => {
          // Don't reject if intentionally cancelled (barge-in)
          if (audioCancelledRef.current) {
            try {
              URL.revokeObjectURL(audioUrl);
            } catch {
              // Ignore
            }
            if (audioUrlRef.current === audioUrl) audioUrlRef.current = null;
            isSpeakingRef.current = false;
            ttsEndTimeRef.current = Date.now();
            audioCancelledRef.current = false;
            ignoreRecognitionUntilRef.current = Date.now() + 900;

            stopBargeInMonitor();
            suspendRecognitionRef.current = false;
            resolve(); // Resolve gracefully
            return;
          }
          try {
            URL.revokeObjectURL(audioUrl);
          } catch {
            // Ignore
          }
          if (audioUrlRef.current === audioUrl) audioUrlRef.current = null;
          isSpeakingRef.current = false;
          ttsEndTimeRef.current = Date.now();
          ignoreRecognitionUntilRef.current = Date.now() + 900;

          stopBargeInMonitor();
          suspendRecognitionRef.current = false;
          reject(new Error('Audio playback failed'));
        };
        
        isSpeakingRef.current = true;
        await audio.play();
      } catch (err) {
        isSpeakingRef.current = false;
        ttsEndTimeRef.current = Date.now();
        ignoreRecognitionUntilRef.current = Date.now() + 900;

        stopBargeInMonitor();
        suspendRecognitionRef.current = false;

        // If stopped or aborted, resolve silently
        if (stoppedRef.current || (err instanceof DOMException && err.name === 'AbortError')) {
          resolve();
          return;
        }

        // Don't reject if intentionally cancelled
        if (audioCancelledRef.current) {
          audioCancelledRef.current = false;
          resolve();
          return;
        }
        reject(err);
      }
    });
  }, [startBargeInMonitor, stopBargeInMonitor]);

  // Process user input and get response
  const processUserInput = useCallback(async (text: string) => {
    if (processingRef.current || !text.trim()) return;
    if (stoppedRef.current || (stateRef.current as VoiceState) === 'idle') return;
    
    processingRef.current = true;
    setIsProcessing(true);
    
    // Use ref to get current mode
    const currentMode = modeRef.current;

    // Push-to-talk: make sure recognition is not running during thinking/speaking.
    if (currentMode === 'push-to-talk' && recognitionRef.current) {
      suspendRecognitionRef.current = true;
      try {
        recognitionRef.current.stop();
      } catch {
        // Ignore
      }
    }
    
    // In realtime mode: stay in 'listening' during thinking (like CLI)
    // In voice-chat mode: show 'thinking' state (turn-based)
    if (currentMode !== 'continuous') {
      setState('thinking');
    }
    // In continuous mode, state stays as 'listening'

    try {
      // Abort any previous query
      try {
        queryAbortRef.current?.abort();
      } catch {
        // Ignore
      }
      const controller = new AbortController();
      queryAbortRef.current = controller;

      // Query the backend
      const response = await apiClient.chat(text, chatSessionIdRef.current, {
        signal: controller.signal,
      });

      if (stoppedRef.current || (stateRef.current as VoiceState) === 'idle') return;

      if (response.answer) {
        if (stoppedRef.current || (stateRef.current as VoiceState) === 'idle') return;

        // Store the response to filter echo
        lastAssistantTextRef.current = response.answer;

        // Keep a small history of assistant utterances for better echo filtering
        assistantUtterancesRef.current = [
          response.answer,
          ...assistantUtterancesRef.current,
        ].slice(0, 3);
        
        // Add assistant response to transcripts
        addTranscript('assistant', response.answer, true);
        
        // Use ref to get current mode (avoid stale closure)
        const currentMode = modeRef.current;
        
        // Update state based on mode
        if (currentMode === 'continuous') {
          // Keep listening - recognition stays active for barge-in
          setState('listening');
        } else {
          setState('speaking');
        }
        
        try {
          await playTTS(response.answer);
        } catch (ttsErr) {
          console.error('TTS playback failed:', ttsErr);
          // Continue even if TTS fails
        }

        if (stoppedRef.current || (stateRef.current as VoiceState) === 'idle') return;
        
        // Clear the echo filter after a short grace period
        setTimeout(() => {
          lastAssistantTextRef.current = '';
        }, 12000);

        // After TTS completes: auto-resume listening
        // Continuous mode resumes via playTTS (single restart point).
        // Push-to-talk resumes here (turn-based).
        setState('listening');
        if (currentMode === 'push-to-talk' && recognitionRef.current) {
          suspendRecognitionRef.current = false;
          ignoreRecognitionUntilRef.current = Date.now() + 900;
          window.setTimeout(() => {
            if (!stoppedRef.current && recognitionRef.current) {
              try {
                recognitionRef.current.start();
              } catch {
                // Already started
              }
            }
          }, 200);
        }
      }
    } catch (err) {
      // Ignore cancellations triggered by Stop
      // (api-client throws APIClientError with code CANCELLED)
      if (stoppedRef.current) return;

      const friendly = getFriendlyError(err);
      toast.error(friendly.title, { description: friendly.message });
      if (!stoppedRef.current && stateRef.current !== 'idle') {
        setState('listening');

        // If push-to-talk was suspended during a turn, allow listening again.
        suspendRecognitionRef.current = false;
        if (modeRef.current === 'push-to-talk' && recognitionRef.current) {
          ignoreRecognitionUntilRef.current = Date.now() + 900;
          try {
            recognitionRef.current.start();
          } catch {
            // Ignore
          }
        }
      }
    } finally {
      processingRef.current = false;
      setIsProcessing(false);
    }
  }, [addTranscript, playTTS]);
  
  // Keep processUserInputRef in sync
  useEffect(() => {
    processUserInputRef.current = processUserInput;
  }, [processUserInput]);

  // Start listening
  const start = useCallback(async () => {
    if (state !== 'idle') return;
    
    // Reset stopped flag when starting fresh
    stoppedRef.current = false;

    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      
      const recognition = initRecognition();
      if (!recognition) {
        toast.error('Speech recognition not supported');
        return;
      }

      recognitionRef.current = recognition;
      recognition.start();
      setState('listening');
    } catch {
      toast.error('Microphone access denied');
    }
  }, [state, initRecognition]);

  // Stop listening (end chat) - handles all edge cases
  const stop = useCallback(() => {
    // Set stopped flag FIRST to prevent onend from restarting
    stoppedRef.current = true;
    audioCancelledRef.current = true;

    // Make handlers see idle immediately (effects can lag)
    stateRef.current = 'idle';

    // Cancel in-flight work
    try {
      queryAbortRef.current?.abort();
    } catch {
      // Ignore
    } finally {
      queryAbortRef.current = null;
    }

    try {
      ttsAbortRef.current?.abort();
    } catch {
      // Ignore
    } finally {
      ttsAbortRef.current = null;
    }
    
    // Stop speech recognition
    try {
      if (recognitionRef.current) {
        recognitionRef.current.onend = null; // Remove handler to prevent restart
        recognitionRef.current.onerror = null;
        recognitionRef.current.onresult = null;
        recognitionRef.current.stop();
      }
    } catch {
      // Ignore - recognition may already be stopped
    } finally {
      recognitionRef.current = null;
    }
    
    // Stop audio playback
    try {
      if (audioRef.current) {
        audioRef.current.onended = null;
        audioRef.current.onerror = null;
        audioRef.current.onpause = null;
        audioRef.current.pause();
        audioRef.current.src = '';
      }
    } catch {
      // Ignore - audio may already be stopped
    } finally {
      audioRef.current = null;
    }

    // Revoke object URL (we removed handlers, so we must clean up ourselves)
    try {
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
        audioUrlRef.current = null;
      }
    } catch {
      // Ignore
    }
    
    // Reset all state flags
    isSpeakingRef.current = false;
    suspendRecognitionRef.current = false;
    stopBargeInMonitor();
    processingRef.current = false;
    lastTranscriptRef.current = '';
    lastAssistantTextRef.current = '';
    
    // Reset UI state
    setState('idle');
    setIsProcessing(false);
  }, [stopBargeInMonitor]);

  // Determine orb state
  const getOrbState = (): VoiceOrbState => {
    if (isProcessing) return 'thinking';
    if (isSpeakingRef.current) return 'speaking';
    return state;
  };

  // Handle orb click - start or stop
  const handleOrbClick = () => {
    if (state === 'idle') {
      start();
    } else {
      stop();
    }
  };

  // Clear transcripts
  const clearTranscripts = useCallback(() => {
    setTranscripts([]);
    lastAssistantTextRef.current = '';
  }, []);

  // Unsupported browser
  if (!isSupported) {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <div
          className={cn(
            'max-w-md w-full p-8 text-center rounded-3xl',
            'bg-white/70 dark:bg-neutral-900/70',
            'backdrop-blur-xl',
            'border border-white/30 dark:border-white/10',
            'shadow-2xl shadow-black/10 dark:shadow-black/30'
          )}
        >
          <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-amber-100/50 dark:bg-amber-900/30 flex items-center justify-center">
            <AlertCircle className="w-8 h-8 text-amber-600 dark:text-amber-400" />
          </div>
          <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
            Voice Not Supported
          </h1>
          <p className="text-neutral-600 dark:text-neutral-400">
            Your browser doesn&apos;t support voice features. Please try using
            Chrome, Edge, or Safari.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-gradient-to-br from-neutral-50 via-white to-neutral-100 dark:from-neutral-950 dark:via-neutral-900 dark:to-neutral-950">
      {/* Main content area */}
      <div className="flex-1 min-h-0 flex flex-col items-center justify-center px-4 py-8">
        {/* Voice Orb - centered with breathing room */}
        <div className="relative mb-16">
          <VoiceOrb
            state={getOrbState()}
            size="xl"
            onClick={handleOrbClick}
          />
          
          {/* Status text below orb */}
          {state === 'idle' ? (
            <div className="absolute -bottom-12 left-1/2 -translate-x-1/2 whitespace-nowrap">
              <p className="text-neutral-500 dark:text-neutral-400 text-sm">
                Tap to start voice chat
              </p>
            </div>
          ) : (
            <div className="absolute -bottom-12 left-1/2 -translate-x-1/2 whitespace-nowrap flex items-center gap-2">
              <div
                className={cn(
                  'w-2 h-2 rounded-full',
                  state === 'listening' && 'bg-green-500 animate-pulse',
                  state === 'thinking' && 'bg-amber-500 animate-pulse',
                  state === 'speaking' && 'bg-blue-500 animate-pulse'
                )}
              />
              <span className="text-neutral-500 dark:text-neutral-400 text-sm capitalize">
                {state === 'listening' ? 'Listening...' : state === 'thinking' ? 'Thinking...' : 'Speaking...'}
              </span>
            </div>
          )}
        </div>

        {/* Transcripts - positioned below orb with good spacing */}
        <div className="w-full max-w-3xl">
          {transcripts.length > 0 ? (
            <div className="space-y-6">
              <VoiceTranscript transcripts={transcripts} className="mx-auto" />
              <button 
                onClick={clearTranscripts}
                className={cn(
                  'text-xs text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300',
                  'transition-colors mx-auto block',
                  'px-4 py-2 rounded-full',
                  'hover:bg-neutral-100/50 dark:hover:bg-neutral-800/50'
                )}
              >
                Clear transcript
              </button>
            </div>
          ) : state === 'idle' ? (
            <div className="text-center text-neutral-500 dark:text-neutral-400">
              <p className="text-sm">
                {mode === 'continuous'
                  ? 'Realtime mode: speak naturally, interrupt anytime'
                  : 'Voice Chat mode: take turns speaking with the AI'}
              </p>
              {mode === 'push-to-talk' && (
                <p className="text-xs mt-2 text-neutral-400 dark:text-neutral-500">
                  Switch to Realtime mode to interrupt while the AI is speaking
                </p>
              )}
            </div>
          ) : mode === 'push-to-talk' ? (
            <div className="text-center mt-4">
              <p className="text-xs text-neutral-400 dark:text-neutral-500">
                Switch to Realtime mode to interrupt while the AI is speaking
              </p>
            </div>
          ) : null}
        </div>
      </div>

      {/* Floating controls at bottom */}
      <div className="sticky bottom-6 px-4 pb-4">
        <VoiceControls
          isListening={state === 'listening'}
          isActive={state !== 'idle'}
          mode={mode}
          onModeChange={setMode}
          onStop={stop}
        />
      </div>
    </div>
  );
}

// Default export wraps the voice page content with error boundary
export default function VoicePage() {
  return (
    <VoiceErrorBoundary>
      <VoicePageContent />
    </VoiceErrorBoundary>
  );
}

// Type declarations for Web Speech API
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
