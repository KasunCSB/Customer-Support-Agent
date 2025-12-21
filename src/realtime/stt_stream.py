"""
Streaming Speech-to-Text Module

Provides continuous speech recognition with:
- Azure Speech SDK continuous recognition
- Partial and final transcript streaming
- Simple barge-in detection when TTS is playing
- Clean state management

Designed for stability - no complex workarounds.
"""

import asyncio
import json
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, List

import azure.cognitiveservices.speech as speechsdk

from src.config import settings
from src.logger import get_logger
from .events import (
    EventBus,
    TranscriptEvent,
    TranscriptType,
    BargeInEvent,
)

logger = get_logger(__name__)


class STTState(Enum):
    """State of the STT stream."""
    IDLE = auto()
    LISTENING = auto()
    PAUSED = auto()
    STOPPED = auto()


@dataclass
class VADConfig:
    """Voice Activity Detection configuration."""
    end_silence_timeout_ms: int = 800       # Silence to end utterance
    initial_silence_timeout_ms: int = 5000  # Wait for initial speech
    min_speech_duration_ms: int = 200       # Minimum speech duration


class STTStream:
    """
    Continuous streaming speech-to-text.

    Uses Azure Speech SDK's continuous recognition mode.
    Emits partial and final transcripts via EventBus.

    Features:
    - Continuous recognition (not one-shot)
    - Partial transcript streaming
    - Simple barge-in detection
    - Clean error handling

    Usage:
        stt = STTStream(event_bus)
        await stt.start()
        # Events published to event_bus
        await stt.stop()
    """

    def __init__(
        self,
        event_bus: EventBus,
        vad_config: Optional[VADConfig] = None,
    ):
        self._event_bus = event_bus
        self._vad_config = vad_config or VADConfig()
        self._state = STTState.IDLE

        # Azure Speech SDK objects
        self._speech_config: Optional[speechsdk.SpeechConfig] = None
        self._audio_config: Optional[speechsdk.audio.AudioConfig] = None
        self._recognizer: Optional[speechsdk.SpeechRecognizer] = None

        # State tracking
        self._current_transcript = ""
        self._last_partial_text = ""
        self._speech_start_time: Optional[float] = None

        # Event loop reference for thread-safe callbacks
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Barge-in detection (simple approach)
        self._tts_playing = False
        self._barge_in_enabled = True
        self._last_barge_in_time = 0.0
        self._barge_in_cooldown_s = 1.0  # Prevent rapid triggers

        self._setup_speech_config()

    def _setup_speech_config(self) -> None:
        """Configure Azure Speech SDK."""
        if not settings.speech.is_configured:
            raise ValueError(
                "Azure Speech not configured. Set AZURE_SPEECH_API_KEY and "
                "AZURE_SPEECH_REGION in .env"
            )

        self._speech_config = speechsdk.SpeechConfig(
            subscription=settings.speech.api_key,
            region=settings.speech.region
        )

        self._speech_config.speech_recognition_language = settings.speech.language
        self._speech_config.request_word_level_timestamps()
        self._speech_config.output_format = speechsdk.OutputFormat.Detailed

        # Configure silence timeouts
        self._speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs,
            str(self._vad_config.end_silence_timeout_ms)
        )
        self._speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs,
            str(self._vad_config.initial_silence_timeout_ms)
        )
        self._speech_config.set_property(
            speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs,
            str(self._vad_config.end_silence_timeout_ms)
        )

        self._audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)

        logger.info(
            f"STT configured: language={settings.speech.language}, "
            f"end_silence={self._vad_config.end_silence_timeout_ms}ms"
        )

    def _create_recognizer(self) -> speechsdk.SpeechRecognizer:
        """Create and configure the speech recognizer."""
        if self._speech_config is None:
            raise RuntimeError("Speech config not initialized")
        
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=self._speech_config,
            audio_config=self._audio_config
        )

        recognizer.recognizing.connect(self._on_recognizing)
        recognizer.recognized.connect(self._on_recognized)
        recognizer.session_started.connect(self._on_session_started)
        recognizer.session_stopped.connect(self._on_session_stopped)
        recognizer.canceled.connect(self._on_canceled)
        recognizer.speech_start_detected.connect(self._on_speech_start)

        return recognizer

    # ========================================================================
    # Event Handlers (called from SDK thread)
    # ========================================================================

    def _on_recognizing(self, evt: speechsdk.SpeechRecognitionEventArgs) -> None:
        """Handle partial recognition results."""
        if evt.result.reason != speechsdk.ResultReason.RecognizingSpeech:
            return

        text = evt.result.text.strip()
        if not text or text == self._last_partial_text:
            return

        self._last_partial_text = text

        # Check for barge-in (user speaking while TTS playing)
        if self._tts_playing and self._barge_in_enabled:
            self._check_barge_in(text)

        # Determine stability
        word_count = len(text.split())
        is_stable = word_count >= 3
        transcript_type = TranscriptType.STABLE if is_stable else TranscriptType.PARTIAL

        event = TranscriptEvent(
            text=text,
            transcript_type=transcript_type,
            confidence=0.7 if is_stable else 0.5,
            is_end_of_turn=False,
        )
        self._publish_event(event)

    def _on_recognized(self, evt: speechsdk.SpeechRecognitionEventArgs) -> None:
        """Handle final recognition results."""
        if evt.result.reason != speechsdk.ResultReason.RecognizedSpeech:
            return

        text = evt.result.text.strip()
        if not text:
            return

        self._current_transcript = text
        self._last_partial_text = ""

        confidence = self._extract_confidence(evt.result)

        event = TranscriptEvent(
            text=text,
            transcript_type=TranscriptType.FINAL,
            confidence=confidence,
            is_end_of_turn=True,
        )
        self._publish_event(event)

        logger.debug(f"Final transcript: {text[:50]}... (conf={confidence:.2f})")

    def _on_session_started(self, evt: speechsdk.SessionEventArgs) -> None:
        """Handle session start."""
        self._state = STTState.LISTENING
        logger.debug(f"STT session started: {evt.session_id}")

    def _on_session_stopped(self, evt: speechsdk.SessionEventArgs) -> None:
        """Handle session stop."""
        self._state = STTState.STOPPED
        logger.debug(f"STT session stopped: {evt.session_id}")

    def _on_canceled(self, evt: speechsdk.SpeechRecognitionCanceledEventArgs) -> None:
        """Handle recognition cancellation."""
        try:
            cancellation = evt.cancellation_details
            if cancellation.reason == speechsdk.CancellationReason.Error:
                logger.error(f"STT error: {cancellation.error_details}")
            elif cancellation.reason == speechsdk.CancellationReason.EndOfStream:
                logger.debug("STT end of stream")
            else:
                logger.debug(f"STT cancelled: {cancellation.reason}")
        except Exception as e:
            logger.error(f"Error handling STT cancellation: {e}")

    def _on_speech_start(self, evt: speechsdk.RecognitionEventArgs) -> None:
        """Handle speech start detection."""
        self._speech_start_time = time.time()
        logger.debug("Speech start detected")

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _extract_confidence(self, result: speechsdk.SpeechRecognitionResult) -> float:
        """Extract confidence score from recognition result."""
        try:
            json_result = result.properties.get(
                speechsdk.PropertyId.SpeechServiceResponse_JsonResult, "{}"
            )
            data = json.loads(json_result)
            if "NBest" in data and len(data["NBest"]) > 0:
                return data["NBest"][0].get("Confidence", 0.9)
        except Exception:
            pass
        return 0.9

    def _publish_event(self, event: TranscriptEvent) -> None:
        """Publish event to event bus (thread-safe)."""
        if self._loop is None:
            return

        try:
            asyncio.run_coroutine_threadsafe(
                self._event_bus.publish(event),
                self._loop
            )
        except Exception as e:
            logger.debug(f"Error publishing event: {e}")

    def _check_barge_in(self, text: str) -> None:
        """Check if user speech should trigger barge-in."""
        now = time.time()

        # Cooldown to prevent rapid triggers
        if now - self._last_barge_in_time < self._barge_in_cooldown_s:
            return

        # Require substantial speech (not just noise)
        words = text.split()
        if len(words) < 2:
            return

        # Ignore common filler sounds
        filler_words = {"uh", "um", "hmm", "mm", "ah"}
        real_words = [w for w in words if w.lower() not in filler_words and len(w) > 1]
        if len(real_words) < 2:
            return

        # Trigger barge-in
        self._last_barge_in_time = now
        event = BargeInEvent(trigger="speech_detected", partial_response=text)

        if self._loop:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._event_bus.publish_immediate(event),
                    self._loop
                )
            except Exception as e:
                logger.debug(f"Error triggering barge-in: {e}")

        logger.info(f"Barge-in triggered: {text[:30]}...")

    # ========================================================================
    # Public API
    # ========================================================================

    async def start(self) -> None:
        """Start continuous speech recognition."""
        if self._state == STTState.LISTENING:
            return

        self._loop = asyncio.get_event_loop()
        self._recognizer = self._create_recognizer()
        self._recognizer.start_continuous_recognition_async()
        self._state = STTState.LISTENING

        logger.info("STT stream started")

    async def stop(self) -> None:
        """Stop speech recognition."""
        if self._state == STTState.STOPPED:
            return

        if self._recognizer:
            try:
                self._recognizer.stop_continuous_recognition_async()
            except Exception as e:
                logger.debug(f"Error stopping recognizer: {e}")
            self._recognizer = None

        self._state = STTState.STOPPED
        logger.info("STT stream stopped")

    async def pause(self) -> None:
        """Pause recognition."""
        if self._recognizer and self._state == STTState.LISTENING:
            self._recognizer.stop_continuous_recognition_async()
            self._state = STTState.PAUSED
            logger.debug("STT paused")

    async def resume(self) -> None:
        """Resume recognition after pause."""
        if self._recognizer and self._state == STTState.PAUSED:
            self._recognizer.start_continuous_recognition_async()
            self._state = STTState.LISTENING
            logger.debug("STT resumed")

    def set_tts_playing(self, playing: bool) -> None:
        """Notify STT that TTS is playing/stopped (for barge-in detection)."""
        self._tts_playing = playing

    def enable_barge_in(self, enabled: bool = True) -> None:
        """Enable or disable barge-in detection."""
        self._barge_in_enabled = enabled

    @property
    def state(self) -> STTState:
        """Get current STT state."""
        return self._state

    @property
    def is_listening(self) -> bool:
        """Check if STT is actively listening."""
        return self._state == STTState.LISTENING

    @property
    def current_transcript(self) -> str:
        """Get current accumulated transcript."""
        return self._current_transcript

    def clear_transcript(self) -> None:
        """Clear current transcript for new turn."""
        self._current_transcript = ""
        self._last_partial_text = ""
