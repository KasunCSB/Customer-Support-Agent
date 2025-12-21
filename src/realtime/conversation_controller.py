"""
Conversation Controller Module

Central orchestrator for real-time voice conversation.
Coordinates STT, Intent, RAG, LLM, and TTS components.

Designed for stability with clean state management and error handling.
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Dict, Any

from src.config import settings
from src.logger import get_logger
from src.core.llm import RAG_SYSTEM_PROMPT

from .events import (
    EventBus,
    TranscriptEvent,
    IntentEvent,
    IntentConfidence,
    RetrievalEvent,
    TurnEvent,
    TurnState,
    BargeInEvent,
)
from .stt_stream import STTStream
from .tts_stream import TTSStream
from .intent_manager import IntentManager
from .llm_stream import AsyncLLMStream, Message
from .rag_engine import RealtimeRAGEngine
from .memory import LayeredMemory

logger = get_logger(__name__)


class ConversationState(Enum):
    """High-level conversation state."""
    INITIALIZING = auto()
    READY = auto()
    LISTENING = auto()
    PROCESSING = auto()
    RESPONDING = auto()
    INTERRUPTED = auto()
    ENDING = auto()
    ERROR = auto()


@dataclass
class ControllerConfig:
    """Configuration for conversation controller."""
    # Latency targets
    target_first_response_ms: int = 500

    # Generation
    max_response_tokens: int = 300

    # Timeouts
    no_speech_timeout_s: float = 30.0
    rag_timeout_s: float = 10.0  # Direct retrieval should be fast

    # Greeting
    auto_greet: bool = True
    greeting_text: str = "Hello! I'm your customer support assistant. How can I help you today?"


class ConversationController:
    """
    Central orchestrator for real-time voice conversation.

    Coordinates all components:
    - STT: Speech recognition
    - Intent: Intent detection
    - RAG: Knowledge retrieval
    - LLM: Response generation
    - TTS: Speech synthesis
    - Memory: Conversation context

    Features:
    - Clean state machine
    - Barge-in support
    - Error recovery
    - Simple event flow

    Usage:
        controller = ConversationController()
        await controller.start()
        await controller.wait_for_completion()
        await controller.stop()
    """

    def __init__(
        self,
        config: Optional[ControllerConfig] = None,
        system_prompt: Optional[str] = None,
    ):
        self._config = config or ControllerConfig()
        self._system_prompt = system_prompt or RAG_SYSTEM_PROMPT

        # Event bus
        self._event_bus = EventBus()

        # Components (initialized lazily)
        self._stt: Optional[STTStream] = None
        self._tts: Optional[TTSStream] = None
        self._intent_manager: Optional[IntentManager] = None
        self._llm: Optional[AsyncLLMStream] = None
        self._rag: Optional[RealtimeRAGEngine] = None

        # Memory
        self._memory = LayeredMemory()

        # State
        self._state = ConversationState.INITIALIZING
        self._running = False

        # Current turn tracking
        self._current_context: Optional[str] = None
        self._response_started = False
        self._greeted = False
        self._response_id = 0  # Track response generation to prevent duplicates

        # Timing
        self._turn_start_time: Optional[float] = None

        # Tasks
        self._event_bus_task: Optional[asyncio.Task] = None
        self._response_task: Optional[asyncio.Task] = None
        self._no_speech_task: Optional[asyncio.Task] = None

    async def _initialize_components(self) -> None:
        """Initialize all conversation components."""
        logger.info("Initializing conversation components...")

        # Create components
        self._stt = STTStream(self._event_bus)
        self._tts = TTSStream(self._event_bus)
        self._intent_manager = IntentManager(self._event_bus)
        self._llm = AsyncLLMStream(self._event_bus)
        self._rag = RealtimeRAGEngine(self._event_bus)

        # Connect TTS to STT for barge-in
        self._tts.set_stt_stream(self._stt)

        # Subscribe to events
        self._event_bus.subscribe(TranscriptEvent, self._handle_transcript)
        self._event_bus.subscribe(IntentEvent, self._handle_intent)
        self._event_bus.subscribe(RetrievalEvent, self._handle_retrieval)
        self._event_bus.subscribe(TurnEvent, self._handle_turn)
        self._event_bus.subscribe(BargeInEvent, self._handle_barge_in)

        # Start components
        await self._intent_manager.start()
        await self._rag.start()

        logger.info("Components initialized")

    async def start(self) -> None:
        """Start the conversation controller."""
        if self._running:
            return

        self._running = True
        self._state = ConversationState.INITIALIZING

        await self._initialize_components()

        # Start event bus
        self._event_bus_task = asyncio.create_task(self._event_bus.run())

        # Start STT (guaranteed to be initialized after _initialize_components)
        if self._stt:
            await self._stt.start()

        self._state = ConversationState.READY

        # Auto-greet
        if self._config.auto_greet:
            await self._speak_response(self._config.greeting_text)
            self._greeted = True

        self._state = ConversationState.LISTENING
        self._reset_no_speech_timer()

        logger.info("Conversation controller started")

    async def stop(self) -> None:
        """Stop the conversation controller."""
        if not self._running:
            return

        self._running = False
        self._state = ConversationState.ENDING

        logger.debug("Stopping conversation controller...")

        # Cancel tasks
        if self._response_task:
            self._response_task.cancel()
            try:
                await asyncio.wait_for(self._response_task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        if self._no_speech_task:
            self._no_speech_task.cancel()
            try:
                await asyncio.wait_for(self._no_speech_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        # Stop components
        if self._tts:
            try:
                await self._tts.stop()
            except Exception as e:
                logger.debug(f"Error stopping TTS: {e}")

        if self._stt:
            try:
                await self._stt.stop()
            except Exception as e:
                logger.debug(f"Error stopping STT: {e}")

        if self._intent_manager:
            try:
                await self._intent_manager.stop()
            except Exception as e:
                logger.debug(f"Error stopping intent manager: {e}")

        if self._rag:
            try:
                await self._rag.stop()
            except Exception as e:
                logger.debug(f"Error stopping RAG: {e}")

        if self._llm:
            try:
                await self._llm.close()
            except Exception as e:
                logger.debug(f"Error closing LLM: {e}")

        # Stop event bus
        self._event_bus.stop()
        if self._event_bus_task:
            self._event_bus_task.cancel()
            try:
                await asyncio.wait_for(self._event_bus_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        await asyncio.sleep(0.3)
        logger.info("Conversation controller stopped")

    async def wait_for_completion(self) -> None:
        """Wait for conversation to complete."""
        while self._running and self._state not in (
            ConversationState.ENDING,
            ConversationState.ERROR,
        ):
            await asyncio.sleep(0.1)

    # ========================================================================
    # Event Handlers
    # ========================================================================

    async def _handle_transcript(self, event: TranscriptEvent) -> None:
        """Handle transcript events from STT."""
        if event.cancelled:
            return

        try:
            await self._memory.update_transcript(event.text, is_final=event.is_final)
            self._reset_no_speech_timer()

            if self._turn_start_time is None:
                self._turn_start_time = time.time()

            if event.is_final:
                self._state = ConversationState.PROCESSING
        except Exception as e:
            logger.error(f"Error handling transcript: {e}")

    async def _handle_intent(self, event: IntentEvent) -> None:
        """Handle intent detection events."""
        if event.cancelled:
            return

        try:
            await self._memory.update_intent(
                event.intent,
                is_confirmed=(event.confidence == IntentConfidence.CONFIRMED),
                entities=event.entities,
            )

            # Handle farewell
            if event.intent == "farewell" and event.confidence == IntentConfidence.CONFIRMED:
                await self._handle_farewell()
                return

            # Handle greeting
            if event.intent == "greeting" and event.confidence == IntentConfidence.CONFIRMED:
                if not self._greeted:
                    await self._speak_response("Hello! How can I help you today?")
                    self._greeted = True
                    self._state = ConversationState.LISTENING
        except Exception as e:
            logger.error(f"Error handling intent: {e}")

    async def _handle_retrieval(self, event: RetrievalEvent) -> None:
        """Handle RAG retrieval events."""
        if event.cancelled:
            logger.debug("Retrieval event cancelled")
            return

        try:
            logger.debug(f"Retrieval event received: {len(event.documents)} documents")
            self._current_context = event.format_context(
                max_tokens=settings.retrieval.context_token_budget
            )
            await self._memory.update_context(self._current_context)
            logger.debug(f"Context set: {len(self._current_context)} chars")
        except Exception as e:
            logger.error(f"Error handling retrieval: {e}")

    async def _handle_turn(self, event: TurnEvent) -> None:
        """Handle turn state change events."""
        if event.cancelled:
            return

        try:
            if event.state == TurnState.PROCESSING:
                await self._start_response_generation(event.user_transcript)
            elif event.state == TurnState.USER_SPEAKING:
                await self._memory.start_turn()
                self._turn_start_time = time.time()
                self._response_started = False
        except Exception as e:
            logger.error(f"Error handling turn: {e}")

    async def _handle_barge_in(self, event: BargeInEvent) -> None:
        """Handle user interruption."""
        logger.info("Barge-in detected - stopping ALL operations")

        try:
            self._state = ConversationState.INTERRUPTED

            # FIRST: Stop TTS immediately - this is the audio overlap source
            if self._tts:
                await self._tts.stop(force=True)

            # Cancel response generation
            if self._response_task and not self._response_task.done():
                self._response_task.cancel()
                try:
                    await asyncio.wait_for(self._response_task, timeout=0.1)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                self._response_task = None

            # Cancel LLM streaming
            if self._llm:
                await self._llm.cancel()

            # Clear any pending context (stops waiting for RAG)
            self._current_context = ""  # Set to empty string, not None

            # Update memory
            await self._memory.update_spoken(event.partial_response, interrupted=True)

            # Reset flags for next turn
            self._response_started = False
            self._response_id += 1

            # Resume listening
            self._state = ConversationState.LISTENING
            self._turn_start_time = time.time()
            
            logger.debug("Barge-in cleanup complete")
        except Exception as e:
            logger.error(f"Error handling barge-in: {e}")
            self._state = ConversationState.LISTENING

    # ========================================================================
    # Response Generation
    # ========================================================================

    async def _start_response_generation(self, user_text: str) -> None:
        """Start generating response."""
        if self._response_started:
            return

        self._response_started = True
        self._response_id += 1
        current_response_id = self._response_id
        self._state = ConversationState.PROCESSING

        # Cancel any existing response task
        if self._response_task and not self._response_task.done():
            self._response_task.cancel()
            try:
                await asyncio.wait_for(self._response_task, timeout=0.5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        # DIRECT RAG retrieval - don't wait for events, fetch directly
        if self._current_context is None and self._rag and user_text:
            rag_start = time.time()
            try:
                logger.debug(f"Fetching RAG context directly for: '{user_text[:50]}...'")
                result = await asyncio.wait_for(
                    self._rag.retrieve(user_text),
                    timeout=self._config.rag_timeout_s
                )
                if result and result.has_results:
                    self._current_context = result.format_context(
                        max_tokens=settings.retrieval.context_token_budget
                    )
                    await self._memory.update_context(self._current_context)
                    rag_time = (time.time() - rag_start) * 1000
                    logger.info(f"RAG retrieved {len(result.documents)} docs in {rag_time:.0f}ms")
                else:
                    logger.debug("RAG returned no results")
            except asyncio.TimeoutError:
                rag_time = (time.time() - rag_start) * 1000
                logger.warning(f"RAG timeout after {rag_time:.0f}ms, proceeding without context")
            except Exception as e:
                logger.error(f"RAG error: {e}")

        # Check if we're still the active response
        if current_response_id != self._response_id:
            logger.debug("Response superseded by newer request")
            return

        # Generate response
        self._response_task = asyncio.create_task(
            self._generate_response(user_text, current_response_id)
        )

    async def _generate_response(self, user_text: str, response_id: Optional[int] = None) -> None:
        """Generate and speak full LLM response."""
        self._state = ConversationState.RESPONDING

        if not self._llm:
            logger.error("LLM not initialized")
            return

        try:
            # Build messages
            messages = self._memory.build_messages(
                system_prompt=self._system_prompt,
                user_text=user_text,
                retrieval_context=self._current_context,
            )
            llm_messages = [Message(**m) for m in messages]

            # Stream response
            response_text = ""
            async for token in self._llm.generate_stream(
                llm_messages,
                max_tokens=self._config.max_response_tokens,
            ):
                if not self._running:
                    break
                # Check if this response is still active
                if response_id is not None and response_id != self._response_id:
                    logger.debug("Response cancelled - newer request pending")
                    return
                response_text += token
                await self._memory.update_generation(response_text)

            # Final check before speaking
            if response_id is not None and response_id != self._response_id:
                logger.debug("Response cancelled before TTS")
                return

            # Speak response
            if response_text.strip():
                latency = 0
                if self._turn_start_time:
                    latency = (time.time() - self._turn_start_time) * 1000
                    logger.info(f"Response latency: {latency:.0f}ms")

                await self._speak_response(response_text.strip())

            # Complete turn
            await self._memory.update_generation(response_text, complete=True)
            await self._memory.end_turn()

            # Reset for next turn
            self._current_context = None
            self._turn_start_time = None
            self._response_started = False
            self._state = ConversationState.LISTENING

        except asyncio.CancelledError:
            logger.debug("Response generation cancelled")
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            await self._speak_response(
                "I'm sorry, I encountered an error. Could you please repeat that?"
            )
            self._state = ConversationState.LISTENING

    async def _handle_farewell(self) -> None:
        """Handle goodbye."""
        await self._speak_response("Goodbye! Have a great day!")
        self._state = ConversationState.ENDING
        self._running = False

    async def _speak_response(self, text: str) -> None:
        """Speak response via TTS."""
        if not text or not self._tts:
            return

        logger.info(f"Agent: {text}")
        await self._memory.update_spoken(text)

        try:
            await self._tts.speak(text)
        except Exception as e:
            logger.error(f"TTS error: {e}")

    # ========================================================================
    # Utility
    # ========================================================================

    def _reset_no_speech_timer(self) -> None:
        """Reset no-speech timeout."""
        if self._no_speech_task:
            self._no_speech_task.cancel()
        self._no_speech_task = asyncio.create_task(self._no_speech_timeout())

    async def _no_speech_timeout(self) -> None:
        """Handle no speech timeout."""
        try:
            await asyncio.sleep(self._config.no_speech_timeout_s)

            if self._running and self._state == ConversationState.LISTENING:
                await self._speak_response(
                    "Are you still there? Let me know if you need any help."
                )
                await asyncio.sleep(self._config.no_speech_timeout_s)

                if self._running and self._state == ConversationState.LISTENING:
                    await self._speak_response(
                        "It seems you've stepped away. Goodbye!"
                    )
                    self._state = ConversationState.ENDING
                    self._running = False
        except asyncio.CancelledError:
            pass

    @property
    def state(self) -> ConversationState:
        """Get current state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if running."""
        return self._running

    @property
    def memory(self) -> LayeredMemory:
        """Get memory system."""
        return self._memory

    @property
    def stats(self) -> Dict[str, Any]:
        """Get controller statistics."""
        return {
            "state": self._state.name,
            "turn_count": self._memory.turn_count,
            "rag_stats": self._rag.stats if self._rag else {},
            "llm_stats": self._llm.stats if self._llm else {},
            "event_bus_latency_ms": self._event_bus.avg_latency_ms,
        }
