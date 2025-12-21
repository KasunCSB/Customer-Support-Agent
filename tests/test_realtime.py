"""
Tests for the real-time voice agent modules.

These tests verify the event system, memory management, intent detection,
and other components that can be tested without Azure services.

Includes a comprehensive integration test for the complete voice chain.
"""

import pytest
import asyncio
from dataclasses import dataclass
from typing import List, Any
from unittest.mock import AsyncMock, MagicMock, patch

# Event system tests
from src.realtime.events import (
    EventBus,
    EventPriority,
    TranscriptEvent,
    TranscriptType,
    IntentEvent,
    IntentConfidence,
    BargeInEvent,
    TurnEvent,
    TurnState,
    RetrievalEvent,
    LLMTokenEvent,
    TTSChunkEvent,
)

# Memory tests
from src.realtime.memory import (
    WorkingMemory,
    SessionMemory,
    LayeredMemory,
    ConversationTurn,
    WorkingMemoryState,
)

# Intent manager tests
from src.realtime.intent_manager import (
    IntentManager,
    TurnBoundaryConfig,
    DEFAULT_INTENT_PATTERNS,
    IntentPattern,
    ResponseType,
)

# Config tests
from src.realtime.voice_agent import VoiceAgentConfig
from src.realtime.stt_stream import VADConfig
from src.realtime.tts_stream import TTSConfig
from src.realtime.rag_engine import RetrievalConfig, RetrievalResult
from src.realtime.llm_stream import GenerationConfig, Message, MicroResponseGenerator
from src.realtime.conversation_controller import ControllerConfig


# ============================================================================
# Event System Tests
# ============================================================================

class TestEventPriority:
    """Tests for event priority system."""
    
    def test_priority_ordering(self):
        """Critical events should have highest priority (lowest value)."""
        assert EventPriority.CRITICAL.value < EventPriority.HIGH.value
        assert EventPriority.HIGH.value < EventPriority.NORMAL.value
        assert EventPriority.NORMAL.value < EventPriority.LOW.value
    
    def test_priority_values(self):
        """Verify expected priority values."""
        assert EventPriority.CRITICAL.value == 0
        assert EventPriority.HIGH.value == 1
        assert EventPriority.NORMAL.value == 2
        assert EventPriority.LOW.value == 3


class TestTranscriptEvent:
    """Tests for TranscriptEvent."""
    
    def test_partial_transcript(self):
        """Test creating a partial transcript event."""
        event = TranscriptEvent(
            text="hello wor",
            transcript_type=TranscriptType.PARTIAL,
        )
        assert event.text == "hello wor"
        assert event.is_final is False
        assert event.transcript_type == TranscriptType.PARTIAL
        assert event.confidence == 0.0
    
    def test_final_transcript(self):
        """Test creating a final transcript event."""
        event = TranscriptEvent(
            text="hello world",
            transcript_type=TranscriptType.FINAL,
            confidence=0.95,
        )
        assert event.text == "hello world"
        assert event.is_final is True
        assert event.confidence == 0.95
    
    def test_is_actionable(self):
        """Test actionable property."""
        # Final is always actionable
        final_event = TranscriptEvent(
            text="hello",
            transcript_type=TranscriptType.FINAL,
        )
        assert final_event.is_actionable is True
        
        # Stable with 3+ words is actionable
        stable_event = TranscriptEvent(
            text="how are you today",
            transcript_type=TranscriptType.STABLE,
        )
        assert stable_event.is_actionable is True


class TestIntentEvent:
    """Tests for IntentEvent."""
    
    def test_speculative_intent(self):
        """Test speculative intent detection."""
        event = IntentEvent(
            intent="billing",
            confidence=IntentConfidence.SPECULATIVE,
            transcript_text="my bill",
        )
        assert event.intent == "billing"
        assert event.confidence == IntentConfidence.SPECULATIVE
        assert event.is_speculative is True
    
    def test_confirmed_intent(self):
        """Test confirmed intent."""
        event = IntentEvent(
            intent="technical_support",
            confidence=IntentConfidence.CONFIRMED,
            transcript_text="my internet is not working",
            entities={"issue_type": "connectivity"},
        )
        assert event.confidence == IntentConfidence.CONFIRMED
        assert event.entities["issue_type"] == "connectivity"
        assert event.is_speculative is False


class TestBargeInEvent:
    """Tests for BargeInEvent."""
    
    def test_barge_in_creation(self):
        """Test barge-in event creation."""
        event = BargeInEvent(
            trigger="speech_detected",
            tts_position_ms=500.0,
        )
        assert event.trigger == "speech_detected"
        assert event.tts_position_ms == 500.0
        assert event.priority == EventPriority.CRITICAL


class TestTurnEvent:
    """Tests for TurnEvent."""
    
    def test_turn_event_creation(self):
        """Test turn event creation."""
        event = TurnEvent(
            state=TurnState.USER_SPEAKING,
            previous_state=TurnState.IDLE,
        )
        assert event.state == TurnState.USER_SPEAKING
        assert event.previous_state == TurnState.IDLE


class TestEventBus:
    """Tests for EventBus pub/sub system."""
    
    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        """Test basic subscribe and publish."""
        bus = EventBus()
        received_events: List[Any] = []
        
        async def handler(event: TranscriptEvent) -> None:
            received_events.append(event)
        
        bus.subscribe(TranscriptEvent, handler)
        
        event = TranscriptEvent(
            text="test",
            transcript_type=TranscriptType.FINAL,
        )
        
        # Use publish_immediate for direct dispatch without event loop
        await bus.publish_immediate(event)
        
        assert len(received_events) == 1
        assert received_events[0].text == "test"
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """Test multiple subscribers for same event type."""
        bus = EventBus()
        count1 = [0]
        count2 = [0]
        
        async def handler1(event: TranscriptEvent) -> None:
            count1[0] += 1
        
        async def handler2(event: TranscriptEvent) -> None:
            count2[0] += 1
        
        bus.subscribe(TranscriptEvent, handler1)
        bus.subscribe(TranscriptEvent, handler2)
        
        event = TranscriptEvent(
            text="test",
            transcript_type=TranscriptType.FINAL,
        )
        await bus.publish_immediate(event)
        
        assert count1[0] == 1
        assert count2[0] == 1
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Test unsubscribing from events."""
        bus = EventBus()
        received = [0]
        
        async def handler(event: TranscriptEvent) -> None:
            received[0] += 1
        
        bus.subscribe(TranscriptEvent, handler)
        bus.unsubscribe(TranscriptEvent, handler)
        
        event = TranscriptEvent(
            text="test",
            transcript_type=TranscriptType.FINAL,
        )
        await bus.publish_immediate(event)
        
        assert received[0] == 0
    
    @pytest.mark.asyncio
    async def test_event_type_filtering(self):
        """Test that handlers only receive their subscribed event types."""
        bus = EventBus()
        transcript_received = [False]
        intent_received = [False]
        
        async def transcript_handler(event: TranscriptEvent) -> None:
            transcript_received[0] = True
        
        async def intent_handler(event: IntentEvent) -> None:
            intent_received[0] = True
        
        bus.subscribe(TranscriptEvent, transcript_handler)
        bus.subscribe(IntentEvent, intent_handler)
        
        # Only publish transcript event
        event = TranscriptEvent(
            text="test",
            transcript_type=TranscriptType.FINAL,
        )
        await bus.publish_immediate(event)
        
        assert transcript_received[0] is True
        assert intent_received[0] is False


# ============================================================================
# Memory Tests
# ============================================================================

class TestWorkingMemory:
    """Tests for WorkingMemory."""
    
    @pytest.mark.asyncio
    async def test_initial_state(self):
        """Test initial working memory state."""
        memory = WorkingMemory()
        assert memory.state.partial_transcript == ""
        assert memory.state.generated_text == ""
        assert memory.state.confirmed_intent == ""
    
    @pytest.mark.asyncio
    async def test_update_transcript(self):
        """Test transcript updates."""
        memory = WorkingMemory()
        await memory.start_turn()
        
        await memory.update_transcript("hello", is_final=False)
        assert memory.state.partial_transcript == "hello"
        
        await memory.update_transcript("hello world", is_final=True)
        assert memory.state.final_transcript == "hello world"
    
    @pytest.mark.asyncio
    async def test_update_intent(self):
        """Test intent updates."""
        memory = WorkingMemory()
        await memory.start_turn()
        
        # Only test confirmed intent (speculative removed in new implementation)
        await memory.update_intent("billing", is_confirmed=True, entities={"amount": "50"})
        assert memory.state.confirmed_intent == "billing"
        assert memory.state.entities["amount"] == "50"
    
    @pytest.mark.asyncio
    async def test_update_context(self):
        """Test context updates."""
        memory = WorkingMemory()
        await memory.start_turn()
        
        await memory.update_context("FAQ answer")
        assert memory.state.retrieval_context == "FAQ answer"
    
    @pytest.mark.asyncio
    async def test_update_generation(self):
        """Test token accumulation."""
        memory = WorkingMemory()
        await memory.start_turn()
        
        await memory.update_generation("Hello world!")
        assert memory.state.generated_text == "Hello world!"
    
    @pytest.mark.asyncio
    async def test_end_turn(self):
        """Test end turn creates conversation turn."""
        memory = WorkingMemory()
        await memory.start_turn()
        await memory.update_transcript("What's my bill?", is_final=True)
        await memory.update_intent("billing", is_confirmed=True)
        await memory.update_generation("Your bill is $50.")
        
        turn = await memory.end_turn()
        
        assert turn.user_text == "What's my bill?"
        assert turn.agent_text == "Your bill is $50."
        assert turn.intent == "billing"


class TestSessionMemory:
    """Tests for SessionMemory."""
    
    def test_initial_state(self):
        """Test initial session state."""
        memory = SessionMemory()
        assert memory.turn_count == 0
        assert len(memory.entities) == 0
    
    def test_add_turn(self):
        """Test adding conversation turns."""
        memory = SessionMemory()
        turn = ConversationTurn(
            turn_id=1,
            user_text="What is my bill?",
            agent_text="Your current bill is $50.",
            intent="billing",
            entities={"amount": "50"},
        )
        memory.add_turn(turn)
        
        assert memory.turn_count == 1
    
    def test_entity_tracking(self):
        """Test entity tracking across turns."""
        memory = SessionMemory()
        
        turn1 = ConversationTurn(
            turn_id=1,
            user_text="My account is 12345",
            agent_text="I see your account.",
            intent="account",
            entities={"account_number": "12345"},
        )
        memory.add_turn(turn1)
        
        turn2 = ConversationTurn(
            turn_id=2,
            user_text="What's my balance?",
            agent_text="Your balance is $100.",
            intent="billing",
            entities={"balance": "100"},
        )
        memory.add_turn(turn2)
        
        assert "account_number" in memory.entities
        assert "balance" in memory.entities
    
    def test_topic_tracking(self):
        """Test topic tracking."""
        memory = SessionMemory()
        
        for i, intent in enumerate(["billing", "billing", "technical_support"]):
            turn = ConversationTurn(
                turn_id=i,
                user_text="test",
                agent_text="test",
                intent=intent,
            )
            memory.add_turn(turn)
        
        assert "billing" in memory.topics
        assert "technical_support" in memory.topics


class TestLayeredMemory:
    """Tests for LayeredMemory integration."""
    
    @pytest.mark.asyncio
    async def test_turn_lifecycle(self):
        """Test complete turn lifecycle in layered memory."""
        memory = LayeredMemory()
        
        # Simulate turn start
        await memory.start_turn()
        
        # Update working memory
        await memory.working.update_transcript("What's my bill?", is_final=True)
        await memory.working.update_intent("billing", is_confirmed=True)
        await memory.working.update_generation("Your bill is $50.")
        
        # Complete turn
        await memory.end_turn()
        
        # Check session was updated
        assert memory.session.turn_count == 1
    
    @pytest.mark.asyncio
    async def test_build_messages_for_llm(self):
        """Test building messages for LLM."""
        memory = LayeredMemory()
        
        # Current turn
        await memory.start_turn()
        await memory.working.update_transcript("What's my bill?", is_final=True)
        await memory.working.update_context("Billing FAQ info")
        
        # Build messages for LLM
        messages = memory.build_messages(
            system_prompt="You are a helpful assistant.",
            user_text="What's my bill?",
            retrieval_context="Billing FAQ info",
        )
        
        # Should have proper message structure
        assert len(messages) >= 2  # system + user
        assert messages[0]["role"] == "system"
        assert "What's my bill?" in messages[-1]["content"]


# ============================================================================
# Intent Manager Tests
# ============================================================================

class TestIntentPatterns:
    """Tests for intent patterns."""
    
    def test_default_patterns_exist(self):
        """Test that default patterns are defined."""
        pattern_names = [p.name for p in DEFAULT_INTENT_PATTERNS]
        assert "greeting" in pattern_names
        assert "farewell" in pattern_names
        assert "billing" in pattern_names
        assert "technical_support" in pattern_names
    
    def test_pattern_structure(self):
        """Test pattern structure."""
        for pattern in DEFAULT_INTENT_PATTERNS:
            assert isinstance(pattern, IntentPattern)
            assert pattern.name
            assert isinstance(pattern.keywords, list)
            assert isinstance(pattern.patterns, list)
            assert isinstance(pattern.response_type, ResponseType)


class TestIntentManager:
    """Tests for IntentManager."""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test intent manager initialization."""
        bus = EventBus()
        manager = IntentManager(event_bus=bus)
        
        assert manager._turn_config is not None
        assert len(manager._intent_patterns) > 0


class TestTurnBoundaryConfig:
    """Tests for TurnBoundaryConfig."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = TurnBoundaryConfig()
        
        assert config.turn_end_threshold_ms > 0
        assert config.enable_backchannels is False  # Disabled by default
    
    def test_custom_values(self):
        """Test custom configuration."""
        config = TurnBoundaryConfig(
            turn_end_threshold_ms=1000,
            enable_backchannels=True,
        )
        
        assert config.turn_end_threshold_ms == 1000
        assert config.enable_backchannels is True


# ============================================================================
# Configuration Tests
# ============================================================================

class TestVoiceAgentConfig:
    """Tests for VoiceAgentConfig."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = VoiceAgentConfig()
        
        assert config.auto_greet is True
        assert config.enable_barge_in is True
        assert config.idle_timeout_seconds == 30.0
    
    def test_custom_values(self):
        """Test custom configuration."""
        config = VoiceAgentConfig(
            auto_greet=False,
            greeting="Welcome!",
            enable_barge_in=False,
        )
        
        assert config.auto_greet is False
        assert config.greeting == "Welcome!"
        assert config.enable_barge_in is False


class TestVADConfig:
    """Tests for VADConfig."""
    
    def test_default_values(self):
        """Test default VAD configuration."""
        config = VADConfig()
        
        assert config.end_silence_timeout_ms > 0
        assert config.initial_silence_timeout_ms > 0
        assert config.min_speech_duration_ms > 0
    
    def test_custom_values(self):
        """Test custom VAD configuration."""
        config = VADConfig(
            end_silence_timeout_ms=1000,
            initial_silence_timeout_ms=10000,
        )
        
        assert config.end_silence_timeout_ms == 1000
        assert config.initial_silence_timeout_ms == 10000


class TestTTSConfig:
    """Tests for TTSConfig."""
    
    def test_default_values(self):
        """Test default TTS configuration."""
        config = TTSConfig()
        
        assert config.voice_name == "en-US-JennyNeural"
        assert config.speaking_rate == 1.0
    
    def test_custom_values(self):
        """Test custom TTS configuration."""
        config = TTSConfig(
            voice_name="en-US-GuyNeural",
            speaking_rate=1.2,
            pitch="+10%",
        )
        
        assert config.voice_name == "en-US-GuyNeural"
        assert config.speaking_rate == 1.2
        assert config.pitch == "+10%"


class TestRetrievalConfig:
    """Tests for RetrievalConfig."""
    
    def test_default_values(self):
        """Test default retrieval configuration."""
        config = RetrievalConfig()
        
        assert config.top_k > 0
        assert config.enable_cache is True
    
    def test_custom_values(self):
        """Test custom retrieval configuration."""
        config = RetrievalConfig(
            top_k=10,
            enable_cache=False,
        )
        
        assert config.top_k == 10
        assert config.enable_cache is False


class TestRetrievalResult:
    """Tests for RetrievalResult."""
    
    def test_result_creation(self):
        """Test retrieval result creation."""
        result = RetrievalResult(
            documents=[{"text": "FAQ answer", "score": 0.9}],
            query="what is my bill",
            retrieval_time_ms=50.0,
            cache_hit=False,
        )
        
        assert len(result.documents) == 1
        assert result.query == "what is my bill"
        assert result.has_results is True
    
    def test_format_context(self):
        """Test context formatting."""
        result = RetrievalResult(
            documents=[
                {"text": "Answer 1", "metadata": {"source": "faq"}},
                {"text": "Answer 2", "metadata": {"source": "docs"}},
            ],
            query="test",
            retrieval_time_ms=50.0,
            cache_hit=False,
        )
        
        context = result.format_context()
        assert "Answer 1" in context
        assert "Answer 2" in context


class TestGenerationConfig:
    """Tests for GenerationConfig."""
    
    def test_default_values(self):
        """Test default generation configuration."""
        config = GenerationConfig()
        
        assert config.temperature >= 0
        assert config.max_tokens > 0
    
    def test_custom_values(self):
        """Test custom generation configuration."""
        config = GenerationConfig(
            temperature=0.5,
            max_tokens=500,
        )
        
        assert config.temperature == 0.5
        assert config.max_tokens == 500


class TestControllerConfig:
    """Tests for ControllerConfig."""
    
    def test_default_values(self):
        """Test default controller configuration."""
        config = ControllerConfig()
        
        assert config.auto_greet is True
        assert config.target_first_response_ms > 0
        assert config.no_speech_timeout_s > 0
    
    def test_custom_values(self):
        """Test custom controller configuration."""
        config = ControllerConfig(
            auto_greet=False,
            target_first_response_ms=300,
            no_speech_timeout_s=60.0,
        )
        
        assert config.auto_greet is False
        assert config.target_first_response_ms == 300
        assert config.no_speech_timeout_s == 60.0


# ============================================================================
# Integration Tests (Event Flow)
# ============================================================================

class TestEventDrivenFlow:
    """Integration tests for event-driven flow."""
    
    @pytest.mark.asyncio
    async def test_transcript_to_intent_flow(self):
        """Test flow from transcript to intent detection."""
        bus = EventBus()
        detected_intents: List[IntentEvent] = []
        
        async def intent_handler(event: IntentEvent) -> None:
            detected_intents.append(event)
        
        bus.subscribe(IntentEvent, intent_handler)
        
        # Simulate intent manager publishing intent after transcript
        intent_event = IntentEvent(
            intent="billing",
            confidence=IntentConfidence.CONFIRMED,
            transcript_text="I have a billing question",
        )
        await bus.publish_immediate(intent_event)
        
        assert len(detected_intents) == 1
        assert detected_intents[0].intent == "billing"
    
    @pytest.mark.asyncio
    async def test_barge_in_priority(self):
        """Test that barge-in events are processed with high priority."""
        bus = EventBus()
        event_order: List[str] = []
        
        async def transcript_handler(event: TranscriptEvent) -> None:
            event_order.append("transcript")
        
        async def barge_in_handler(event: BargeInEvent) -> None:
            event_order.append("barge_in")
        
        bus.subscribe(TranscriptEvent, transcript_handler)
        bus.subscribe(BargeInEvent, barge_in_handler)
        
        # Publish both events
        transcript = TranscriptEvent(
            text="test",
            transcript_type=TranscriptType.FINAL,
        )
        barge_in = BargeInEvent(
            trigger="speech_detected",
        )
        
        await bus.publish_immediate(transcript)
        await bus.publish_immediate(barge_in)
        
        # Both should be processed
        assert "transcript" in event_order
        assert "barge_in" in event_order
    
    @pytest.mark.asyncio
    async def test_event_cancellation(self):
        """Test event cancellation."""
        event = TranscriptEvent(
            text="test",
            transcript_type=TranscriptType.PARTIAL,
        )
        
        assert event.cancelled is False
        event.cancel()
        assert event.cancelled is True
    
    @pytest.mark.asyncio
    async def test_event_age_tracking(self):
        """Test event age calculation."""
        event = TranscriptEvent(
            text="test",
            transcript_type=TranscriptType.PARTIAL,
        )
        
        # Wait a bit
        await asyncio.sleep(0.1)
        
        # Age should be approximately 100ms
        assert event.age_ms >= 90  # Allow some tolerance
        assert event.age_ms < 200


class TestConversationTurn:
    """Tests for ConversationTurn dataclass."""
    
    def test_turn_creation(self):
        """Test conversation turn creation."""
        turn = ConversationTurn(
            turn_id=1,
            user_text="Hello",
            agent_text="Hi there!",
            intent="greeting",
        )
        
        assert turn.turn_id == 1
        assert turn.user_text == "Hello"
        assert turn.agent_text == "Hi there!"
        assert turn.intent == "greeting"
    
    def test_to_messages(self):
        """Test conversion to LLM messages."""
        turn = ConversationTurn(
            turn_id=1,
            user_text="What's my bill?",
            agent_text="Your bill is $50.",
        )
        
        messages = turn.to_messages()
        
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "What's my bill?"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Your bill is $50."


# ============================================================================
# Voice Chain Integration Tests
# ============================================================================

class TestVoiceChainIntegration:
    """Integration tests for the complete voice processing chain."""

    @pytest.mark.asyncio
    async def test_complete_turn_flow(self):
        """Test complete turn flow: transcript -> intent -> retrieval -> response."""
        bus = EventBus()
        memory = LayeredMemory()
        
        # Track all events
        events_received: List[Any] = []
        
        async def track_transcript(event: TranscriptEvent):
            events_received.append(("transcript", event))
        
        async def track_intent(event: IntentEvent):
            events_received.append(("intent", event))
        
        async def track_retrieval(event: RetrievalEvent):
            events_received.append(("retrieval", event))
        
        bus.subscribe(TranscriptEvent, track_transcript)
        bus.subscribe(IntentEvent, track_intent)
        bus.subscribe(RetrievalEvent, track_retrieval)
        
        # Start turn
        await memory.start_turn()
        
        # Simulate transcript event
        transcript = TranscriptEvent(
            text="What is my account balance?",
            transcript_type=TranscriptType.FINAL,
            is_end_of_turn=True,
        )
        await bus.publish_immediate(transcript)
        await memory.update_transcript(transcript.text, is_final=True)
        
        # Simulate intent detection
        intent = IntentEvent(
            intent="billing",
            confidence=IntentConfidence.CONFIRMED,
            transcript_text=transcript.text,
            requires_retrieval=True,
        )
        await bus.publish_immediate(intent)
        await memory.update_intent(intent.intent, is_confirmed=True)
        
        # Simulate retrieval
        retrieval = RetrievalEvent(
            query=transcript.text,
            documents=[
                {"text": "Your current balance is $150.00", "metadata": {"source": "billing_faq"}}
            ],
        )
        await bus.publish_immediate(retrieval)
        await memory.update_context(retrieval.format_context())
        
        # Generate response
        response = "Based on your account, your current balance is $150.00."
        await memory.update_generation(response)
        
        # End turn
        turn = await memory.end_turn()
        
        # Verify complete flow
        assert len([e for e in events_received if e[0] == "transcript"]) == 1
        assert len([e for e in events_received if e[0] == "intent"]) == 1
        assert len([e for e in events_received if e[0] == "retrieval"]) == 1
        
        assert turn.user_text == "What is my account balance?"
        assert turn.intent == "billing"
        assert turn.agent_text == response

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self):
        """Test multi-turn conversation with memory persistence."""
        memory = LayeredMemory()
        
        # Turn 1
        await memory.start_turn()
        await memory.update_transcript("Hello", is_final=True)
        await memory.update_intent("greeting", is_confirmed=True)
        await memory.update_generation("Hi! How can I help you?")
        await memory.end_turn()
        
        # Turn 2
        await memory.start_turn()
        await memory.update_transcript("What's my bill?", is_final=True)
        await memory.update_intent("billing", is_confirmed=True)
        await memory.update_generation("Your bill is $50.")
        await memory.end_turn()
        
        # Verify session state
        assert memory.turn_count == 2
        assert "greeting" in memory.session_topics
        assert "billing" in memory.session_topics
        
        # Verify history building
        history = memory.get_history()
        assert len(history) == 4  # 2 turns * 2 messages each

    @pytest.mark.asyncio
    async def test_barge_in_handling(self):
        """Test barge-in event handling."""
        bus = EventBus()
        barge_in_received = []
        
        async def barge_in_handler(event: BargeInEvent):
            barge_in_received.append(event)
        
        bus.subscribe(BargeInEvent, barge_in_handler)
        
        # Emit barge-in event
        barge_in = BargeInEvent(
            trigger="speech_detected",
            tts_position_ms=500.0,
        )
        await bus.publish_immediate(barge_in)
        
        assert len(barge_in_received) == 1
        assert barge_in_received[0].trigger == "speech_detected"
        assert barge_in_received[0].priority == EventPriority.CRITICAL

    @pytest.mark.asyncio
    async def test_intent_detection_patterns(self):
        """Test various intent detection patterns using direct detection."""
        bus = EventBus()
        manager = IntentManager(bus)
        
        # Test the internal _detect_intent method directly
        # This tests the pattern matching logic without event bus complexity
        test_cases = [
            ("hello", "greeting"),
            ("I have a problem with my bill", "billing"),
            ("My internet is broken", "technical_support"),
            ("Thank you goodbye", "farewell"),
        ]
        
        for text, expected_intent in test_cases:
            from src.realtime.events import IntentConfidence
            intent = manager._detect_intent(text, IntentConfidence.CONFIRMED)
            
            assert intent is not None, f"No intent detected for: {text}"
            assert intent.intent == expected_intent, \
                f"Expected {expected_intent} for '{text}', got {intent.intent}"


class TestMicroResponseGenerator:
    """Tests for MicroResponseGenerator."""
    
    def test_backchannel_generation(self):
        """Test backchannel response generation."""
        gen = MicroResponseGenerator()
        backchannels = [gen.get_backchannel() for _ in range(10)]
        
        # Should return valid backchannels
        for bc in backchannels:
            assert bc in MicroResponseGenerator.BACKCHANNELS
    
    def test_acknowledgement_generation(self):
        """Test acknowledgement response generation."""
        gen = MicroResponseGenerator()
        acks = [gen.get_acknowledgement() for _ in range(10)]
        
        # Should return valid acknowledgements
        for ack in acks:
            assert ack in MicroResponseGenerator.ACKNOWLEDGEMENTS
    
    def test_thinking_response_generation(self):
        """Test thinking response generation."""
        gen = MicroResponseGenerator()
        thinking = [gen.get_thinking() for _ in range(10)]
        
        # Should return valid thinking responses
        for t in thinking:
            assert t in MicroResponseGenerator.THINKING


class TestMessageConstruction:
    """Tests for Message class construction."""
    
    def test_message_to_dict(self):
        """Test message to dictionary conversion."""
        msg = Message(role="user", content="Hello")
        d = msg.to_dict()
        
        assert d["role"] == "user"
        assert d["content"] == "Hello"
    
    def test_message_from_dict(self):
        """Test message from dictionary."""
        data = {"role": "assistant", "content": "Hi there!"}
        msg = Message(**data)
        
        assert msg.role == "assistant"
        assert msg.content == "Hi there!"


class TestRetrievalResultFormatting:
    """Tests for RetrievalResult formatting."""
    
    def test_format_with_sources(self):
        """Test formatting with source information."""
        result = RetrievalResult(
            documents=[
                {"text": "Answer 1", "metadata": {"source": "FAQ.md"}},
                {"text": "Answer 2", "metadata": {"source": "Guide.txt"}},
            ],
            query="test query",
            retrieval_time_ms=25.0,
            cache_hit=False,
        )
        
        context = result.format_context(include_source=True)
        
        assert "[1. FAQ.md]" in context
        assert "[2. Guide.txt]" in context
        assert "Answer 1" in context
        assert "Answer 2" in context
    
    def test_format_without_sources(self):
        """Test formatting without source information."""
        result = RetrievalResult(
            documents=[
                {"text": "Answer 1", "metadata": {"source": "FAQ.md"}},
            ],
            query="test query",
            retrieval_time_ms=25.0,
            cache_hit=False,
        )
        
        context = result.format_context(include_source=False)
        
        assert "[1. FAQ.md]" not in context
        assert "Answer 1" in context
    
    def test_empty_documents(self):
        """Test with empty documents."""
        result = RetrievalResult(
            documents=[],
            query="test query",
            retrieval_time_ms=10.0,
            cache_hit=False,
        )
        
        assert result.has_results is False
        assert result.format_context() == ""


class TestTTSTextSplitting:
    """Tests for TTS text splitting logic."""
    
    def test_split_by_sentences(self):
        """Test splitting long text by sentences."""
        from src.realtime.tts_stream import TTSStream
        
        text = "First sentence. Second sentence. Third sentence."
        chunks = TTSStream._split_text(text, max_len=30)
        
        assert len(chunks) >= 2
        # Verify each chunk is a complete sentence
        for chunk in chunks:
            chunk = chunk.strip()
            if chunk:
                assert chunk.endswith(".")
    
    def test_short_text_not_split(self):
        """Test that short text is not split."""
        from src.realtime.tts_stream import TTSStream
        
        text = "Hello world."
        chunks = TTSStream._split_text(text, max_len=300)
        
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_empty_text(self):
        """Test handling of empty text."""
        from src.realtime.tts_stream import TTSStream
        
        chunks = TTSStream._split_text("", max_len=300)
        assert chunks == []
        
        chunks = TTSStream._split_text("   ", max_len=300)
        assert chunks == []
