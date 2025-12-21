"""
Event System for Real-Time Voice Agent

Provides a simple, efficient async event bus for coordinating all real-time components.
Designed for stability and low latency.

Event Types:
- TranscriptEvent: Speech recognition results (partial/final)
- IntentEvent: Detected user intent
- RetrievalEvent: RAG retrieval results
- LLMTokenEvent: Streaming tokens from LLM
- TTSChunkEvent: Audio chunks for playback
- BargeInEvent: User interruption signal
- TurnEvent: Turn state changes
"""

import asyncio
import time
import uuid
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

from src.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound="Event")
EventHandler = Callable[[T], Awaitable[None]]


class EventPriority(Enum):
    """Priority levels for event processing."""
    CRITICAL = 0  # Barge-in, cancellation
    HIGH = 1      # Turn boundaries, intent
    NORMAL = 2    # Transcripts, tokens
    LOW = 3       # Logging, analytics


@dataclass
class Event(ABC):
    """Base event class for all real-time events."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    timestamp: float = field(default_factory=time.time)
    priority: EventPriority = EventPriority.NORMAL
    cancelled: bool = False
    source: str = ""

    def cancel(self) -> None:
        """Mark this event as cancelled."""
        self.cancelled = True

    @property
    def age_ms(self) -> float:
        """Get event age in milliseconds."""
        return (time.time() - self.timestamp) * 1000


# ============================================================================
# Speech-to-Text Events
# ============================================================================

class TranscriptType(Enum):
    """Type of transcript result."""
    PARTIAL = auto()   # Interim result, may change
    STABLE = auto()    # High confidence partial
    FINAL = auto()     # Recognition complete
    ENDPOINT = auto()  # End of speech detected


@dataclass
class TranscriptEvent(Event):
    """Speech recognition result."""
    text: str = ""
    transcript_type: TranscriptType = TranscriptType.PARTIAL
    confidence: float = 0.0
    word_timestamps: List[Dict[str, Any]] = field(default_factory=list)
    is_end_of_turn: bool = False
    silence_duration_ms: float = 0.0
    language: str = "en-US"
    source: str = "stt"

    @property
    def is_final(self) -> bool:
        return self.transcript_type in (TranscriptType.FINAL, TranscriptType.ENDPOINT)

    @property
    def is_actionable(self) -> bool:
        """Check if we should process this transcript."""
        if self.is_final:
            return True
        if self.transcript_type == TranscriptType.STABLE and len(self.text.split()) >= 3:
            return True
        return self.is_end_of_turn


# ============================================================================
# Intent Events
# ============================================================================

class IntentConfidence(Enum):
    """Confidence level for detected intent."""
    SPECULATIVE = auto()  # Based on partial transcript
    LIKELY = auto()       # High confidence from stable partial
    CONFIRMED = auto()    # From final transcript


@dataclass
class IntentEvent(Event):
    """Detected user intent."""
    intent: str = ""
    entities: Dict[str, Any] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)
    confidence: IntentConfidence = IntentConfidence.SPECULATIVE
    transcript_text: str = ""
    requires_retrieval: bool = True
    suggested_response_type: str = "informational"
    priority: EventPriority = EventPriority.HIGH
    source: str = "intent_manager"

    @property
    def is_speculative(self) -> bool:
        return self.confidence == IntentConfidence.SPECULATIVE


# ============================================================================
# RAG Events
# ============================================================================

@dataclass
class RetrievalEvent(Event):
    """RAG retrieval results."""
    query: str = ""
    documents: List[Dict[str, Any]] = field(default_factory=list)
    is_speculative: bool = False
    retrieval_time_ms: float = 0.0
    cache_hit: bool = False
    source: str = "rag_engine"

    @property
    def has_results(self) -> bool:
        return len(self.documents) > 0

    def format_context(self, max_tokens: int = 2000) -> str:
        """Format documents as LLM context."""
        if not self.documents:
            return ""

        parts = []
        for i, doc in enumerate(self.documents[:5]):
            text = doc.get("text", "")
            source = doc.get("source", doc.get("metadata", {}).get("source", "Knowledge Base"))
            parts.append(f"[{i + 1}. {source}]\n{text}")

        context = "\n\n".join(parts)
        max_chars = max_tokens * 4
        if len(context) > max_chars:
            context = context[:max_chars] + "..."
        return context


# ============================================================================
# LLM Events
# ============================================================================

@dataclass
class LLMTokenEvent(Event):
    """Streaming token from LLM generation."""
    token: str = ""
    token_index: int = 0
    is_first: bool = False
    is_last: bool = False
    accumulated_text: str = ""
    finish_reason: str = ""
    generation_id: str = ""
    source: str = "llm"

    @property
    def is_speakable(self) -> bool:
        """Check if accumulated text has a complete speakable unit."""
        text = self.accumulated_text.strip()
        return any(text.endswith(p) for p in ".!?:,;") or len(text.split()) >= 8


# ============================================================================
# TTS Events
# ============================================================================

@dataclass
class TTSChunkEvent(Event):
    """Audio chunk from TTS synthesis."""
    audio_data: bytes = b""
    text_segment: str = ""
    is_first: bool = False
    is_last: bool = False
    duration_ms: float = 0.0
    synthesis_id: str = ""
    word_boundary: Optional[Dict[str, Any]] = None
    source: str = "tts"


# ============================================================================
# Control Events
# ============================================================================

@dataclass
class BargeInEvent(Event):
    """User interruption detected - triggers immediate stop of TTS/LLM."""
    trigger: str = "speech_detected"
    tts_position_ms: float = 0.0
    partial_response: str = ""
    priority: EventPriority = EventPriority.CRITICAL
    source: str = "barge_in_detector"


class TurnState(Enum):
    """State of conversation turn."""
    IDLE = auto()
    USER_SPEAKING = auto()
    USER_PAUSED = auto()
    PROCESSING = auto()
    AGENT_SPEAKING = auto()
    INTERRUPTED = auto()


@dataclass
class TurnEvent(Event):
    """Turn state change notification."""
    state: TurnState = TurnState.IDLE
    previous_state: TurnState = TurnState.IDLE
    user_transcript: str = ""
    agent_response: str = ""
    turn_duration_ms: float = 0.0
    priority: EventPriority = EventPriority.HIGH
    source: str = "turn_manager"


class ConversationPhase(Enum):
    """High-level conversation phase."""
    GREETING = auto()
    INFORMATION_GATHERING = auto()
    PROBLEM_SOLVING = auto()
    CONFIRMATION = auto()
    CLOSING = auto()


@dataclass
class ConversationEvent(Event):
    """High-level conversation state change."""
    phase: ConversationPhase = ConversationPhase.GREETING
    topic: str = ""
    sentiment: str = "neutral"
    escalation_needed: bool = False
    source: str = "conversation_controller"


@dataclass
class AudioChunkEvent(Event):
    """Raw audio chunk from microphone."""
    audio_data: bytes = b""
    sample_rate: int = 16000
    channels: int = 1
    duration_ms: float = 0.0
    is_speech: bool = False
    energy_level: float = 0.0
    source: str = "audio_input"


# ============================================================================
# Event Bus
# ============================================================================

class EventBus:
    """
    Simple async event bus for real-time event coordination.

    Features:
    - Async publish/subscribe
    - Priority-based processing
    - Direct dispatch for critical events
    """

    def __init__(self, max_queue_size: int = 500):
        self._handlers: Dict[type, List[EventHandler]] = {}
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_queue_size)
        self._running: bool = False
        self._event_count: int = 0
        self._latency_samples: List[float] = []

    def subscribe(self, event_type: type, handler: EventHandler) -> None:
        """Subscribe to events of a specific type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]

    async def publish(self, event: Event) -> None:
        """Queue an event for processing."""
        if event.cancelled:
            return

        self._event_count += 1
        queue_item = (event.priority.value, self._event_count, event)

        try:
            self._queue.put_nowait(queue_item)
        except asyncio.QueueFull:
            logger.warning(f"Event queue full, dropping {type(event).__name__}")

    async def publish_immediate(self, event: Event) -> None:
        """Immediately dispatch an event (bypass queue)."""
        await self._dispatch(event)

    async def _dispatch(self, event: Event) -> None:
        """Dispatch event to all registered handlers."""
        if event.cancelled:
            return

        latency = event.age_ms
        self._latency_samples.append(latency)
        if len(self._latency_samples) > 100:
            self._latency_samples.pop(0)

        handlers = []
        for registered_type, type_handlers in self._handlers.items():
            if isinstance(event, registered_type):
                handlers.extend(type_handlers)

        if not handlers:
            return

        for handler in handlers:
            try:
                await handler(event)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Handler error for {type(event).__name__}: {e}")

    async def run(self) -> None:
        """Start the event processing loop."""
        self._running = True
        logger.debug("Event bus started")

        while self._running:
            try:
                _, _, event = await asyncio.wait_for(
                    self._queue.get(), timeout=0.1
                )
                await self._dispatch(event)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event bus error: {e}")

        logger.debug("Event bus stopped")

    def stop(self) -> None:
        """Stop the event processing loop."""
        self._running = False

    @property
    def avg_latency_ms(self) -> float:
        """Get average event processing latency."""
        if not self._latency_samples:
            return 0.0
        return sum(self._latency_samples) / len(self._latency_samples)

    @property
    def queue_size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()

    async def drain(self, timeout: float = 5.0) -> None:
        """Wait for queue to empty."""
        try:
            await asyncio.wait_for(self._queue.join(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Event queue drain timed out")
