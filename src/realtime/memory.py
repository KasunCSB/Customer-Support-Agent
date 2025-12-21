"""
Layered Memory System Module

Provides multi-tier memory for conversational context:
- Working Memory: Current turn context
- Session Memory: Conversation history

Designed for stability with simple, clean interfaces.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from collections import deque

from src.logger import get_logger
from .events import TurnState

logger = get_logger(__name__)


@dataclass
class ConversationTurn:
    """Single conversation turn."""
    turn_id: int
    user_text: str
    agent_text: str
    intent: str = ""
    entities: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    was_interrupted: bool = False

    def to_messages(self) -> List[Dict[str, str]]:
        """Convert to LLM message format."""
        return [
            {"role": "user", "content": self.user_text},
            {"role": "assistant", "content": self.agent_text},
        ]


@dataclass
class WorkingMemoryState:
    """Current turn working memory."""
    turn_state: TurnState = TurnState.IDLE
    turn_start_time: Optional[float] = None
    partial_transcript: str = ""
    final_transcript: str = ""
    confirmed_intent: str = ""
    entities: Dict[str, Any] = field(default_factory=dict)
    retrieval_context: str = ""
    generated_text: str = ""
    spoken_text: str = ""
    was_interrupted: bool = False


class WorkingMemory:
    """
    Fast working memory for current turn.

    Holds immediate context that changes during a single turn.
    """

    def __init__(self):
        self._state = WorkingMemoryState()
        self._lock = asyncio.Lock()

    async def start_turn(self) -> None:
        """Initialize for new turn."""
        async with self._lock:
            self._state = WorkingMemoryState(
                turn_state=TurnState.USER_SPEAKING,
                turn_start_time=time.time(),
            )

    async def update_transcript(self, text: str, is_final: bool = False) -> None:
        """Update transcript text."""
        async with self._lock:
            if is_final:
                self._state.final_transcript = text
            else:
                self._state.partial_transcript = text

    async def update_intent(
        self,
        intent: str,
        is_confirmed: bool = False,
        entities: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update detected intent."""
        async with self._lock:
            if is_confirmed:
                self._state.confirmed_intent = intent
            if entities:
                self._state.entities.update(entities)

    async def update_context(self, context: str) -> None:
        """Update retrieved context."""
        async with self._lock:
            self._state.retrieval_context = context

    async def update_generation(self, text: str) -> None:
        """Update generation state."""
        async with self._lock:
            self._state.generated_text = text

    async def update_spoken(self, text: str, interrupted: bool = False) -> None:
        """Update spoken response state."""
        async with self._lock:
            self._state.spoken_text = text
            self._state.was_interrupted = interrupted

    async def end_turn(self) -> ConversationTurn:
        """End turn and create turn record."""
        async with self._lock:
            turn = ConversationTurn(
                turn_id=0,  # Set by session memory
                user_text=self._state.final_transcript or self._state.partial_transcript,
                agent_text=self._state.generated_text,
                intent=self._state.confirmed_intent,
                entities=self._state.entities,
                was_interrupted=self._state.was_interrupted,
            )
            return turn

    @property
    def user_text(self) -> str:
        """Get current user text."""
        return self._state.final_transcript or self._state.partial_transcript

    @property
    def context(self) -> str:
        """Get current retrieval context."""
        return self._state.retrieval_context

    @property
    def state(self) -> WorkingMemoryState:
        """Get current state."""
        return self._state


class SessionMemory:
    """
    Session-level conversation memory.

    Maintains conversation history for the current session.
    """

    def __init__(self, max_turns: int = 20):
        self._max_turns = max_turns
        self._turns: deque[ConversationTurn] = deque(maxlen=max_turns)
        self._turn_counter = 0
        self._session_start = time.time()
        self._session_entities: Dict[str, Any] = {}
        self._intent_history: List[str] = []

    def add_turn(self, turn: ConversationTurn) -> None:
        """Add completed turn to history."""
        self._turn_counter += 1
        turn.turn_id = self._turn_counter
        self._turns.append(turn)

        if turn.entities:
            self._session_entities.update(turn.entities)
        if turn.intent:
            self._intent_history.append(turn.intent)

    def get_history(
        self,
        max_turns: Optional[int] = None,
        include_summary: bool = True,
    ) -> List[Dict[str, str]]:
        """Get conversation history as messages."""
        messages = []
        turns = list(self._turns)
        if max_turns:
            turns = turns[-max_turns:]

        for turn in turns:
            messages.extend(turn.to_messages())

        return messages

    def clear(self) -> None:
        """Clear session memory."""
        self._turns.clear()
        self._turn_counter = 0
        self._session_entities.clear()
        self._intent_history.clear()

    @property
    def turn_count(self) -> int:
        """Get total turns in session."""
        return self._turn_counter

    @property
    def entities(self) -> Dict[str, Any]:
        """Get all entities extracted in session."""
        return self._session_entities.copy()

    @property
    def topics(self) -> List[str]:
        """Get unique topics discussed."""
        return list(dict.fromkeys(self._intent_history))

    @property
    def session_topics(self) -> List[str]:
        """Alias for topics."""
        return self.topics


class LayeredMemory:
    """
    Multi-tier memory system for conversational AI.

    Combines:
    - Working Memory: Current turn (fast, volatile)
    - Session Memory: Conversation history

    Usage:
        memory = LayeredMemory()
        await memory.start_turn()
        await memory.update_transcript("Hello")
        await memory.end_turn()
    """

    def __init__(
        self,
        max_session_turns: int = 20,
        context_token_budget: int = 2000,
    ):
        self._working = WorkingMemory()
        self._session = SessionMemory(max_turns=max_session_turns)
        self._context_budget = context_token_budget

    # Working Memory Operations
    async def start_turn(self) -> None:
        """Start new conversation turn."""
        await self._working.start_turn()

    async def update_transcript(self, text: str, is_final: bool = False) -> None:
        """Update current turn transcript."""
        await self._working.update_transcript(text, is_final)

    async def update_intent(
        self,
        intent: str,
        is_confirmed: bool = False,
        entities: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update detected intent."""
        await self._working.update_intent(intent, is_confirmed, entities)

    async def update_context(
        self,
        context: str,
        documents: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Update retrieved RAG context."""
        await self._working.update_context(context)

    async def update_generation(self, tokens: str, complete: bool = False) -> None:
        """Update generation state."""
        await self._working.update_generation(tokens)

    async def update_spoken(self, text: str, interrupted: bool = False) -> None:
        """Update spoken response."""
        await self._working.update_spoken(text, interrupted)

    async def end_turn(self) -> ConversationTurn:
        """End current turn and move to session memory."""
        turn = await self._working.end_turn()

        if turn.user_text and turn.agent_text:
            self._session.add_turn(turn)

        return turn

    # Context Building
    def build_messages(
        self,
        system_prompt: str,
        user_text: Optional[str] = None,
        retrieval_context: Optional[str] = None,
        max_history_turns: int = 5,
    ) -> List[Dict[str, str]]:
        """Build complete message list for LLM."""
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        history = self._session.get_history(max_turns=max_history_turns)
        messages.extend(history)

        # Build current user message with context
        current_text = user_text or self._working.user_text
        current_context = retrieval_context or self._working.context

        if current_context:
            user_content = f"Context:\n{current_context}\n\nCustomer: \"{current_text}\""
        else:
            user_content = f"Customer: \"{current_text}\""

        messages.append({"role": "user", "content": user_content})

        return messages

    def get_history(self, max_turns: Optional[int] = None) -> List[Dict[str, str]]:
        """Get conversation history."""
        return self._session.get_history(max_turns)

    def clear_session(self) -> None:
        """Clear session memory."""
        self._session.clear()

    @property
    def working(self) -> WorkingMemory:
        """Access working memory."""
        return self._working

    @property
    def session(self) -> SessionMemory:
        """Access session memory."""
        return self._session

    @property
    def turn_count(self) -> int:
        """Get session turn count."""
        return self._session.turn_count

    @property
    def session_entities(self) -> Dict[str, Any]:
        """Get session entities."""
        return self._session.entities

    @property
    def session_topics(self) -> List[str]:
        """Get session topics."""
        return self._session.topics
