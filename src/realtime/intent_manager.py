"""
Intent Manager Module

Provides intent detection from transcripts for:
- Early RAG retrieval triggering
- Turn boundary detection
- Response type prediction

Simple pattern-based intent detection without LLM overhead.
"""

import asyncio
import re
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, List, Dict, Any

from src.logger import get_logger
from .events import (
    EventBus,
    TranscriptEvent,
    TranscriptType,
    IntentEvent,
    IntentConfidence,
    TurnEvent,
    TurnState,
)

logger = get_logger(__name__)


class ResponseType(Enum):
    """Type of response expected."""
    ACKNOWLEDGEMENT = auto()
    INFORMATIONAL = auto()
    ACTION = auto()
    FAREWELL = auto()
    CLARIFICATION = auto()


@dataclass
class IntentPattern:
    """Pattern for intent detection."""
    name: str
    keywords: List[str]
    patterns: List[str]  # Regex patterns
    response_type: ResponseType
    requires_rag: bool = True
    priority: int = 0


# Pre-defined intent patterns
DEFAULT_INTENT_PATTERNS = [
    IntentPattern(
        name="greeting",
        keywords=["hello", "hi", "hey", "good morning", "good afternoon"],
        patterns=[r"^(hi|hello|hey)\b", r"good (morning|afternoon|evening)"],
        response_type=ResponseType.ACKNOWLEDGEMENT,
        requires_rag=False,
        priority=10,
    ),
    IntentPattern(
        name="farewell",
        keywords=["bye", "goodbye", "thanks", "thank you", "see you"],
        patterns=[r"\b(bye|goodbye|see you)\b", r"^thanks?\b", r"that'?s all"],
        response_type=ResponseType.FAREWELL,
        requires_rag=False,
        priority=10,
    ),
    IntentPattern(
        name="billing",
        keywords=["bill", "payment", "charge", "invoice", "price", "cost", "fee"],
        patterns=[r"\b(bill|payment|charge|invoice|price|cost|fee)s?\b"],
        response_type=ResponseType.INFORMATIONAL,
        requires_rag=True,
        priority=5,
    ),
    IntentPattern(
        name="technical_support",
        keywords=["not working", "broken", "error", "problem", "issue", "help"],
        patterns=[r"\b(not working|broken|error|problem|issue)\b", r"can'?t\s+\w+"],
        response_type=ResponseType.INFORMATIONAL,
        requires_rag=True,
        priority=5,
    ),
    IntentPattern(
        name="account",
        keywords=["account", "password", "login", "sign in", "profile"],
        patterns=[r"\b(account|password|login|sign.?in|profile)\b"],
        response_type=ResponseType.INFORMATIONAL,
        requires_rag=True,
        priority=5,
    ),
    IntentPattern(
        name="package_inquiry",
        keywords=["package", "plan", "subscription", "data", "minutes", "sms"],
        patterns=[r"\b(package|plan|subscription|data|minutes|sms)\b"],
        response_type=ResponseType.INFORMATIONAL,
        requires_rag=True,
        priority=5,
    ),
    IntentPattern(
        name="confirmation",
        keywords=["yes", "yeah", "correct", "right", "exactly", "sure"],
        patterns=[r"^(yes|yeah|yep|correct|right|exactly|sure)\b"],
        response_type=ResponseType.ACKNOWLEDGEMENT,
        requires_rag=False,
        priority=3,
    ),
    IntentPattern(
        name="negation",
        keywords=["no", "nope", "not really", "wrong"],
        patterns=[r"^(no|nope|not really|wrong)\b"],
        response_type=ResponseType.CLARIFICATION,
        requires_rag=False,
        priority=3,
    ),
]


@dataclass
class TurnBoundaryConfig:
    """Configuration for turn boundary detection."""
    turn_end_threshold_ms: int = 800
    enable_backchannels: bool = False  # Disabled by default for stability


class IntentManager:
    """
    Manages intent detection and turn boundary recognition.

    Features:
    - Pattern-based intent detection
    - Turn completion detection
    - Event publishing

    Usage:
        manager = IntentManager(event_bus)
        await manager.start()
        # Subscribes to TranscriptEvent and emits IntentEvent
    """

    def __init__(
        self,
        event_bus: EventBus,
        turn_config: Optional[TurnBoundaryConfig] = None,
        intent_patterns: Optional[List[IntentPattern]] = None,
    ):
        self._event_bus = event_bus
        self._turn_config = turn_config or TurnBoundaryConfig()
        self._intent_patterns = intent_patterns or DEFAULT_INTENT_PATTERNS

        # Compile regex patterns
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        for pattern in self._intent_patterns:
            self._compiled_patterns[pattern.name] = [
                re.compile(p, re.IGNORECASE) for p in pattern.patterns
            ]

        # State tracking
        self._current_turn_state = TurnState.IDLE
        self._turn_start_time: Optional[float] = None
        self._current_transcript = ""
        self._last_emitted_intent: Optional[IntentEvent] = None

    async def start(self) -> None:
        """Start the intent manager."""
        self._event_bus.subscribe(TranscriptEvent, self._handle_transcript)
        logger.info("Intent manager started")

    async def stop(self) -> None:
        """Stop the intent manager."""
        self._event_bus.unsubscribe(TranscriptEvent, self._handle_transcript)
        logger.info("Intent manager stopped")

    async def _handle_transcript(self, event: TranscriptEvent) -> None:
        """Process transcript event and detect intent."""
        if event.cancelled:
            return

        text = event.text.strip()
        if not text:
            return

        self._current_transcript = text

        # Update turn state
        if self._current_turn_state == TurnState.IDLE:
            await self._start_turn()

        # Detect intent based on transcript type
        if event.transcript_type == TranscriptType.PARTIAL:
            await self._process_partial(event)
        elif event.transcript_type == TranscriptType.STABLE:
            await self._process_stable(event)
        elif event.is_final:
            await self._process_final(event)

        # Check for turn boundary
        if event.is_end_of_turn:
            await self._end_turn(event)

    async def _process_partial(self, event: TranscriptEvent) -> None:
        """Process partial transcript for speculative intent."""
        detected = self._detect_intent(event.text, IntentConfidence.SPECULATIVE)
        if detected and self._should_emit(detected):
            await self._emit_intent(detected)

    async def _process_stable(self, event: TranscriptEvent) -> None:
        """Process stable partial for likely intent."""
        detected = self._detect_intent(event.text, IntentConfidence.LIKELY)
        if detected:
            await self._emit_intent(detected)

    async def _process_final(self, event: TranscriptEvent) -> None:
        """Process final transcript for confirmed intent."""
        detected = self._detect_intent(event.text, IntentConfidence.CONFIRMED)
        if detected:
            await self._emit_intent(detected)

    def _detect_intent(
        self,
        text: str,
        confidence: IntentConfidence,
    ) -> Optional[IntentEvent]:
        """Detect intent from text using patterns."""
        text_lower = text.lower()

        best_match: Optional[IntentPattern] = None
        best_priority = -1

        for pattern in self._intent_patterns:
            # Check keywords
            for keyword in pattern.keywords:
                if keyword in text_lower:
                    if pattern.priority > best_priority:
                        best_match = pattern
                        best_priority = pattern.priority
                    break

            # Check regex patterns
            for compiled in self._compiled_patterns.get(pattern.name, []):
                if compiled.search(text_lower):
                    if pattern.priority > best_priority:
                        best_match = pattern
                        best_priority = pattern.priority
                    break

        if best_match:
            return IntentEvent(
                intent=best_match.name,
                confidence=confidence,
                transcript_text=text,
                requires_retrieval=best_match.requires_rag,
                keywords=best_match.keywords[:3],
                suggested_response_type=best_match.response_type.name.lower(),
            )

        # Default to general query
        if len(text.split()) >= 3:
            return IntentEvent(
                intent="general_query",
                confidence=confidence,
                transcript_text=text,
                requires_retrieval=True,
            )

        return None

    def _should_emit(self, intent: IntentEvent) -> bool:
        """Check if intent should be emitted."""
        if self._last_emitted_intent is None:
            return True
        if intent.intent != self._last_emitted_intent.intent:
            return True
        if intent.confidence.value > self._last_emitted_intent.confidence.value:
            return True
        return False

    async def _emit_intent(self, intent: IntentEvent) -> None:
        """Emit intent event."""
        self._last_emitted_intent = intent
        await self._event_bus.publish(intent)
        logger.debug(f"Intent detected: {intent.intent} ({intent.confidence.name})")

    async def _start_turn(self) -> None:
        """Start new turn."""
        self._current_turn_state = TurnState.USER_SPEAKING
        self._turn_start_time = time.time()
        self._last_emitted_intent = None

        await self._event_bus.publish(
            TurnEvent(
                state=TurnState.USER_SPEAKING,
                previous_state=TurnState.IDLE,
            )
        )

    async def _end_turn(self, event: TranscriptEvent) -> None:
        """End current turn."""
        duration_ms = 0.0
        if self._turn_start_time:
            duration_ms = (time.time() - self._turn_start_time) * 1000

        await self._event_bus.publish(
            TurnEvent(
                state=TurnState.PROCESSING,
                previous_state=self._current_turn_state,
                user_transcript=event.text,
                turn_duration_ms=duration_ms,
            )
        )

        self._current_turn_state = TurnState.IDLE
        self._turn_start_time = None

    def reset(self) -> None:
        """Reset state for new conversation."""
        self._current_turn_state = TurnState.IDLE
        self._turn_start_time = None
        self._current_transcript = ""
        self._last_emitted_intent = None
