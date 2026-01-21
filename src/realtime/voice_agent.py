"""
Real-Time Voice Agent Module

Main entry point for the real-time conversational voice agent.
Provides a simple interface to start and manage voice conversations.

Designed for stability with clean configuration and error handling.
"""

import asyncio
import signal
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable

from src.config import settings
from src.logger import get_logger
from src.core.llm import VOICE_RAG_SYSTEM_PROMPT

from .conversation_controller import ConversationController, ControllerConfig, ConversationState

logger = get_logger(__name__)


@dataclass
class VoiceAgentConfig:
    """Configuration for voice agent."""
    # System prompt
    system_prompt: str = VOICE_RAG_SYSTEM_PROMPT

    # Greeting
    auto_greet: bool = True
    greeting: str = "Hello! I'm Rashmi, your customer support assistant. How can I help you today?"

    # Features
    enable_barge_in: bool = True

    # Timeouts
    idle_timeout_seconds: float = 30.0


class RealtimeVoiceAgent:
    """
    Real-time voice agent with full-duplex conversation.

    Features:
    - Natural voice conversation
    - Barge-in support (interrupt while speaking)
    - RAG-powered knowledge retrieval
    - Clean error handling

    Usage:
        agent = RealtimeVoiceAgent()
        await agent.run()

    Or with custom config:
        config = VoiceAgentConfig(
            greeting="Welcome to support!",
            enable_barge_in=True,
        )
        agent = RealtimeVoiceAgent(config)
        await agent.run()
    """

    def __init__(
        self,
        config: Optional[VoiceAgentConfig] = None,
        on_state_change: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize voice agent.

        Args:
            config: Agent configuration
            on_state_change: Callback on state changes
        """
        self._config = config or VoiceAgentConfig()
        self._on_state_change = on_state_change

        # Create controller config
        controller_config = ControllerConfig(
            no_speech_timeout_s=self._config.idle_timeout_seconds,
            auto_greet=self._config.auto_greet,
            greeting_text=self._config.greeting,
        )

        # Create controller
        self._controller = ConversationController(
            config=controller_config,
            system_prompt=self._config.system_prompt,
        )

        self._running = False
        self._shutdown_event = asyncio.Event()

    async def run(self) -> None:
        """
        Run the voice agent.

        Starts listening and responding until user says goodbye or Ctrl+C.
        """
        self._running = True

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._signal_handler)
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass

        try:
            await self._controller.start()
            logger.info("Voice agent running - speak to interact, say 'goodbye' to exit")

            while self._running and self._controller.is_running:
                await asyncio.sleep(0.1)

                if self._on_state_change:
                    self._on_state_change(self._controller.state.name)

        except asyncio.CancelledError:
            logger.info("Voice agent cancelled")
        except Exception as e:
            logger.error(f"Voice agent error: {e}")
            raise
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the voice agent."""
        if not self._running:
            return

        logger.debug("Stopping voice agent...")
        self._running = False

        try:
            await self._controller.stop()
        except Exception as e:
            logger.error(f"Error stopping controller: {e}")

        await asyncio.sleep(0.3)
        logger.info("Voice agent stopped")

    def _signal_handler(self) -> None:
        """Handle shutdown signals."""
        logger.info("Shutdown signal received")
        self._running = False
        self._shutdown_event.set()

    @property
    def is_running(self) -> bool:
        """Check if agent is running."""
        return self._running

    @property
    def state(self) -> str:
        """Get current state name."""
        return self._controller.state.name

    @property
    def stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return self._controller.stats

    @property
    def turn_count(self) -> int:
        """Get number of completed turns."""
        return self._controller.memory.turn_count

    @property
    def session_topics(self) -> list:
        """Get topics discussed in session."""
        return self._controller.memory.session_topics


async def run_voice_agent(
    system_prompt: Optional[str] = None,
    greeting: Optional[str] = None,
    enable_barge_in: bool = True,
) -> None:
    """
    Convenience function to run voice agent.

    Args:
        system_prompt: Custom system prompt
        greeting: Custom greeting message
        enable_barge_in: Allow user to interrupt
    """
    config = VoiceAgentConfig(
        system_prompt=system_prompt or VOICE_RAG_SYSTEM_PROMPT,
        greeting=greeting or VoiceAgentConfig.greeting,
        enable_barge_in=enable_barge_in,
    )

    agent = RealtimeVoiceAgent(config)
    await agent.run()


def print_banner() -> None:
    """Print agent startup banner."""
    print("\n" + "=" * 60)
    print("🎙️  Real-Time Voice Agent")
    print("=" * 60)
    print("Features:")
    print("  • Full-duplex conversation")
    print("  • Barge-in support (interrupt anytime)")
    print("  • RAG-powered knowledge retrieval")
    print("-" * 60)
    print("Controls:")
    print("  • Speak naturally to interact")
    print("  • Say 'goodbye' or 'exit' to end")
    print("  • Press Ctrl+C to force quit")
    print("-" * 60)
