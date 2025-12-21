"""
Streaming Text-to-Speech Module

Provides real-time speech synthesis with:
- Azure Neural TTS
- Simple, reliable synthesis
- Barge-in support (instant stop on user speech)
- Clean error handling with single retry

Designed for stability - no complex workarounds.
"""

import asyncio
import time
import threading
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, List, Dict, Any

import azure.cognitiveservices.speech as speechsdk

from src.config import settings
from src.logger import get_logger
from .events import EventBus, TTSChunkEvent, BargeInEvent

logger = get_logger(__name__)


class TTSState(Enum):
    """State of the TTS stream."""
    IDLE = auto()
    SYNTHESIZING = auto()
    STOPPED = auto()


class SynthesisResult(Enum):
    """Result of a synthesis attempt."""
    SUCCESS = auto()      # Completed successfully
    CANCELLED = auto()    # Stopped due to barge-in (expected, don't retry)
    ERROR = auto()        # Actual error (should retry)


@dataclass
class TTSConfig:
    """TTS configuration."""
    voice_name: str = "en-US-JennyNeural"
    speaking_rate: float = 1.0
    pitch: str = "+0%"
    volume: str = "medium"
    synthesis_timeout_s: float = 30.0  # Timeout per chunk (increased for long responses)


class TTSStream:
    """
    Streaming text-to-speech with Azure Neural TTS.

    Features:
    - Reliable synthesis with timeout protection
    - Single retry on failure
    - Barge-in support (instant stop via controlled audio)
    - SSML support for natural speech

    Usage:
        tts = TTSStream(event_bus)
        await tts.speak("Hello, how can I help?")
        await tts.stop()  # On barge-in
    """

    def __init__(
        self,
        event_bus: EventBus,
        config: Optional[TTSConfig] = None,
    ):
        self._event_bus = event_bus
        self._config = config or TTSConfig(voice_name=settings.speech.voice_name)
        self._state = TTSState.IDLE

        # Azure Speech SDK
        self._speech_config: Optional[speechsdk.SpeechConfig] = None
        self._synthesizer: Optional[speechsdk.SpeechSynthesizer] = None
        self._active_synthesizer: Optional[speechsdk.SpeechSynthesizer] = None  # Currently speaking

        # State tracking
        self._synthesis_cancelled = asyncio.Event()
        self._current_synthesis_id = ""
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._audio_stopped = asyncio.Event()  # Signals when audio fully stopped
        self._audio_stopped.set()  # Initially not playing

        # Mutex to prevent overlapping TTS
        self._speak_lock = asyncio.Lock()
        
        # Thread-safe stop flag for barge-in
        self._stop_audio_flag = threading.Event()

        # STT reference for coordination
        self._stt_stream: Optional[Any] = None

        self._setup_speech_config()

    def _setup_speech_config(self) -> None:
        """Configure Azure Speech SDK for TTS."""
        if not settings.speech.is_configured:
            raise ValueError(
                "Azure Speech not configured. Set AZURE_SPEECH_API_KEY and "
                "AZURE_SPEECH_REGION in .env"
            )

        self._speech_config = speechsdk.SpeechConfig(
            subscription=settings.speech.api_key,
            region=settings.speech.region
        )

        self._speech_config.speech_synthesis_voice_name = self._config.voice_name
        # Use PCM format for direct speaker output (MP3 may not play through speakers)
        self._speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
        )

        logger.info(f"TTS configured: voice={self._config.voice_name}")

    def _create_synthesizer(self) -> speechsdk.SpeechSynthesizer:
        """Create speech synthesizer with speaker output."""
        if self._speech_config is None:
            raise RuntimeError("Speech config not initialized")
        
        audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
        
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self._speech_config,
            audio_config=audio_config
        )

        synthesizer.synthesis_started.connect(self._on_synthesis_started)
        synthesizer.synthesis_completed.connect(self._on_synthesis_completed)
        synthesizer.synthesis_canceled.connect(self._on_synthesis_canceled)

        return synthesizer

    # ========================================================================
    # Event Handlers
    # ========================================================================

    def _on_synthesis_started(self, evt: speechsdk.SpeechSynthesisEventArgs) -> None:
        """Handle synthesis start."""
        self._state = TTSState.SYNTHESIZING
        if self._stt_stream:
            self._stt_stream.set_tts_playing(True)
        logger.debug("TTS synthesis started")

    def _on_synthesis_completed(self, evt: speechsdk.SpeechSynthesisEventArgs) -> None:
        """Handle synthesis completion."""
        self._state = TTSState.IDLE
        if self._stt_stream:
            self._stt_stream.set_tts_playing(False)
        logger.debug("TTS synthesis completed")

    def _on_synthesis_canceled(self, evt: speechsdk.SpeechSynthesisEventArgs) -> None:
        """Handle synthesis cancellation."""
        self._state = TTSState.IDLE
        if self._stt_stream:
            self._stt_stream.set_tts_playing(False)

        try:
            if evt.result and evt.result.cancellation_details:
                details = evt.result.cancellation_details
                if details.reason == speechsdk.CancellationReason.Error:
                    logger.error(f"TTS error: {details.error_details}")
                else:
                    logger.debug("TTS cancelled")
        except Exception as e:
            logger.debug(f"Error in TTS cancel handler: {e}")

    # ========================================================================
    # SSML Generation
    # ========================================================================

    def _build_ssml(self, text: str, rate: Optional[float] = None) -> str:
        """Build SSML for speech synthesis."""
        rate = rate or self._config.speaking_rate
        pitch = self._config.pitch
        volume = self._config.volume

        ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
    <voice name="{self._config.voice_name}">
        <prosody rate="{rate}" pitch="{pitch}" volume="{volume}">
            {self._escape_ssml(text)}
        </prosody>
    </voice>
</speak>"""
        return ssml

    @staticmethod
    def _escape_ssml(text: str) -> str:
        """Escape special characters for SSML."""
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;")
        )

    @staticmethod
    def _split_text(text: str, max_len: int = 300) -> List[str]:
        """Split text into chunks at sentence boundaries."""
        if len(text) <= max_len:
            return [text.strip()] if text.strip() else []

        chunks = []
        sentences = []
        current = ""
        
        # Split by sentence endings
        for char in text:
            current += char
            if char in ".!?" and len(current.strip()) > 0:
                sentences.append(current.strip())
                current = ""
        
        if current.strip():
            sentences.append(current.strip())

        # Group sentences into chunks
        chunk = ""
        for sentence in sentences:
            if len(chunk) + len(sentence) + 1 <= max_len:
                chunk = f"{chunk} {sentence}".strip()
            else:
                if chunk:
                    chunks.append(chunk)
                chunk = sentence

        if chunk:
            chunks.append(chunk)

        return [c for c in chunks if c]

    # ========================================================================
    # Public API
    # ========================================================================

    async def speak(
        self,
        text: str,
        rate: Optional[float] = None,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        Synthesize and speak text.

        Args:
            text: Text to speak
            rate: Speaking rate override
            timeout: Synthesis timeout

        Returns:
            True if completed successfully, False if interrupted/failed
        """
        if not text or not text.strip():
            return True

        # Wait for previous audio to completely stop
        await self._audio_stopped.wait()
        
        async with self._speak_lock:
            # Mark that audio is now playing
            self._audio_stopped.clear()
            try:
                return await self._speak_impl(text, rate, timeout)
            finally:
                # Mark that audio has stopped
                self._audio_stopped.set()

    async def _speak_impl(
        self,
        text: str,
        rate: Optional[float],
        timeout: Optional[float],
    ) -> bool:
        """Internal speak implementation."""
        self._loop = asyncio.get_event_loop()
        
        # CRITICAL: Clear ALL stop flags before starting new speech
        self._synthesis_cancelled.clear()
        self._stop_audio_flag.clear()
        self._state = TTSState.IDLE  # Reset state
        
        timeout = timeout or self._config.synthesis_timeout_s

        # Split into manageable chunks
        chunks = self._split_text(text, max_len=300)
        if not chunks:
            return True

        self._current_synthesis_id = f"tts_{int(time.time())}"

        try:
            for chunk in chunks:
                if self._synthesis_cancelled.is_set():
                    return False

                result = await self._synthesize_chunk(chunk, rate, timeout)
                
                if result == SynthesisResult.SUCCESS:
                    continue  # Move to next chunk
                elif result == SynthesisResult.CANCELLED:
                    # Barge-in occurred - stop gracefully, no retry needed
                    logger.debug(f"TTS stopped (barge-in) for: {chunk[:30]}...")
                    return False
                else:  # SynthesisResult.ERROR
                    # Actual error - retry once
                    logger.warning(f"TTS error, retrying: {chunk[:30]}...")
                    await asyncio.sleep(0.2)
                    retry_result = await self._synthesize_chunk(chunk, rate, timeout)
                    if retry_result != SynthesisResult.SUCCESS:
                        logger.error(f"TTS failed after retry: {chunk[:30]}...")
                        return False

            return True

        except asyncio.CancelledError:
            logger.debug("TTS speak cancelled")
            return False
        finally:
            self._state = TTSState.IDLE
            if self._stt_stream:
                self._stt_stream.set_tts_playing(False)

    async def _synthesize_chunk(
        self,
        text: str,
        rate: Optional[float],
        timeout: float,
    ) -> SynthesisResult:
        """Synthesize a single chunk of text with barge-in support.
        
        Returns:
            SynthesisResult.SUCCESS - Completed successfully
            SynthesisResult.CANCELLED - Stopped due to barge-in
            SynthesisResult.ERROR - Actual synthesis error
        """
        # Check cancellation before starting (these should already be cleared by _speak_impl)
        if self._synthesis_cancelled.is_set():
            logger.debug("TTS chunk skipped - cancelled flag set")
            return SynthesisResult.CANCELLED
            
        synthesizer: Optional[speechsdk.SpeechSynthesizer] = None
        
        try:
            if self._speech_config is None:
                logger.error("Speech config not initialized")
                return SynthesisResult.ERROR
                
            ssml = self._build_ssml(text, rate)
            
            # Use default speaker output
            audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self._speech_config,
                audio_config=audio_config
            )
            
            # Connect callbacks
            synthesizer.synthesis_started.connect(self._on_synthesis_started)
            synthesizer.synthesis_completed.connect(self._on_synthesis_completed)
            synthesizer.synthesis_canceled.connect(self._on_synthesis_canceled)
            
            self._active_synthesizer = synthesizer  # Track active synthesizer

            # Start async synthesis (returns a future)
            result_future = synthesizer.speak_ssml_async(ssml)
            
            # Run blocking .get() in executor
            loop = asyncio.get_event_loop()
            
            def blocking_wait():
                """Wait for synthesis result."""
                try:
                    return result_future.get()
                except Exception as e:
                    logger.debug(f"Synthesis wait error: {e}")
                    return None
            
            # Create task for blocking wait
            executor_task = loop.run_in_executor(None, blocking_wait)
            
            # Wait with timeout, checking for barge-in periodically
            start_time = time.time()
            
            while not executor_task.done():
                # Check barge-in flags
                if self._synthesis_cancelled.is_set() or self._stop_audio_flag.is_set():
                    try:
                        synthesizer.stop_speaking_async()
                    except Exception:
                        pass
                    logger.debug("TTS chunk stopped via barge-in")
                    return SynthesisResult.CANCELLED
                
                # Check timeout
                if time.time() - start_time > timeout:
                    try:
                        synthesizer.stop_speaking_async()
                    except Exception:
                        pass
                    logger.warning(f"TTS timeout for: {text[:30]}...")
                    return SynthesisResult.ERROR
                
                # Wait a bit before checking again
                await asyncio.sleep(0.05)
            
            # Get the result
            result = await executor_task

            # Check result
            if result is None:
                return SynthesisResult.ERROR

            if result.reason == speechsdk.ResultReason.Canceled:
                if self._synthesis_cancelled.is_set():
                    return SynthesisResult.CANCELLED
                details = result.cancellation_details
                if details and details.reason == speechsdk.CancellationReason.Error:
                    logger.debug(f"Synthesis error: {details.error_details}")
                return SynthesisResult.ERROR

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return SynthesisResult.SUCCESS
            return SynthesisResult.ERROR

        except asyncio.CancelledError:
            logger.debug("TTS chunk cancelled")
            if synthesizer:
                try:
                    synthesizer.stop_speaking_async()
                except Exception:
                    pass
            return SynthesisResult.CANCELLED
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return SynthesisResult.ERROR
        finally:
            # Clear active synthesizer when done
            if self._active_synthesizer == synthesizer:
                self._active_synthesizer = None

    async def stop(self, force: bool = True) -> None:
        """Stop current synthesis (for barge-in) - instant stop."""
        logger.debug("TTS stop() called - instant stop requested")
        
        # Set thread-safe stop flag FIRST (checked in synthesis loop)
        self._stop_audio_flag.set()
        
        # Set async cancelled flag
        self._synthesis_cancelled.set()
        self._state = TTSState.STOPPED

        # Stop the currently active synthesizer immediately
        synth = self._active_synthesizer
        if synth:
            try:
                # Fire and forget - don't wait for completion
                synth.stop_speaking_async()
            except Exception as e:
                logger.debug(f"Error stopping active synthesizer: {e}")
            finally:
                self._active_synthesizer = None
        
        # Also stop the main synthesizer if exists
        if self._synthesizer:
            try:
                self._synthesizer.stop_speaking_async()
            except Exception as e:
                logger.debug(f"Error stopping synthesizer: {e}")
        
        # Signal that audio has stopped
        self._audio_stopped.set()
        
        logger.debug("TTS stop() complete")

        if self._stt_stream:
            self._stt_stream.set_tts_playing(False)

        # Publish stop event
        event = TTSChunkEvent(
            audio_data=b"",
            is_last=True,
            synthesis_id=self._current_synthesis_id,
        )
        await self._event_bus.publish(event)

        logger.debug("TTS stopped")

    def set_stt_stream(self, stt_stream: Any) -> None:
        """Set reference to STT stream for coordination."""
        self._stt_stream = stt_stream

    async def handle_barge_in(self, event: BargeInEvent) -> None:
        """Handle barge-in event by stopping synthesis."""
        if self._state == TTSState.SYNTHESIZING:
            logger.info("TTS barge-in - stopping synthesis")
            await self.stop()

    @property
    def state(self) -> TTSState:
        """Get current TTS state."""
        return self._state

    @property
    def is_speaking(self) -> bool:
        """Check if TTS is currently speaking."""
        return self._state == TTSState.SYNTHESIZING
