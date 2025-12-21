"""
Real-Time Conversational Voice Agent Module

This package provides a low-latency voice conversation system
with an event-driven, streaming architecture.

Architecture:
- Event Bus: Async event coordination
- STT Stream: Continuous speech recognition with VAD
- TTS Stream: Streaming audio synthesis with barge-in
- Intent Manager: Turn detection and intent extraction
- RAG Engine: Async retrieval with caching
- LLM Stream: Token streaming with cancellation
- Conversation Controller: Orchestrates conversation flow
- Memory System: Working and session memory

Design Goals:
- Stability first
- Clean error handling
- Simple state management
- Barge-in support

Usage:
    from src.realtime import RealtimeVoiceAgent

    agent = RealtimeVoiceAgent()
    await agent.run()
"""

from .events import (
    Event,
    EventBus,
    EventPriority,
    AudioChunkEvent,
    TranscriptEvent,
    TranscriptType,
    IntentEvent,
    IntentConfidence,
    RetrievalEvent,
    LLMTokenEvent,
    TTSChunkEvent,
    BargeInEvent,
    TurnEvent,
    TurnState,
    ConversationEvent,
    ConversationPhase,
)
from .stt_stream import STTStream, STTState, VADConfig
from .tts_stream import TTSStream, TTSState, TTSConfig
from .intent_manager import IntentManager, ResponseType, TurnBoundaryConfig, IntentPattern
from .llm_stream import AsyncLLMStream, Message, GenerationConfig, MicroResponseGenerator
from .rag_engine import RealtimeRAGEngine, RetrievalConfig, RetrievalResult
from .memory import LayeredMemory, WorkingMemory, SessionMemory, ConversationTurn
from .conversation_controller import ConversationController, ControllerConfig, ConversationState
from .voice_agent import RealtimeVoiceAgent, VoiceAgentConfig, run_voice_agent, print_banner

__all__ = [
    # Events
    "Event",
    "EventBus",
    "EventPriority",
    "AudioChunkEvent",
    "TranscriptEvent",
    "TranscriptType",
    "IntentEvent",
    "IntentConfidence",
    "RetrievalEvent",
    "LLMTokenEvent",
    "TTSChunkEvent",
    "BargeInEvent",
    "TurnEvent",
    "TurnState",
    "ConversationEvent",
    "ConversationPhase",
    # STT
    "STTStream",
    "STTState",
    "VADConfig",
    # TTS
    "TTSStream",
    "TTSState",
    "TTSConfig",
    # Intent
    "IntentManager",
    "ResponseType",
    "TurnBoundaryConfig",
    "IntentPattern",
    # LLM
    "AsyncLLMStream",
    "Message",
    "GenerationConfig",
    "MicroResponseGenerator",
    # RAG
    "RealtimeRAGEngine",
    "RetrievalConfig",
    "RetrievalResult",
    # Memory
    "LayeredMemory",
    "WorkingMemory",
    "SessionMemory",
    "ConversationTurn",
    # Controller
    "ConversationController",
    "ControllerConfig",
    "ConversationState",
    # Voice Agent
    "RealtimeVoiceAgent",
    "VoiceAgentConfig",
    "run_voice_agent",
    "print_banner",
]
