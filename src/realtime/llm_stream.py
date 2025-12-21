"""
Async Streaming LLM Module

Provides asynchronous streaming LLM generation with:
- Azure OpenAI streaming API
- Token-by-token delivery
- Mid-generation cancellation
- Clean error handling with single retry

Designed for stability - no complex workarounds.
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any, AsyncIterator

import aiohttp

from src.config import settings
from src.logger import get_logger
from .events import EventBus, LLMTokenEvent, BargeInEvent

logger = get_logger(__name__)


class GenerationState(Enum):
    """State of LLM generation."""
    IDLE = auto()
    GENERATING = auto()
    COMPLETED = auto()
    CANCELLED = auto()
    ERROR = auto()


@dataclass
class Message:
    """Chat message for LLM."""
    role: str  # system, user, assistant
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class GenerationConfig:
    """Configuration for LLM generation."""
    temperature: float = 0.7
    max_tokens: int = 300
    presence_penalty: float = 0.1
    frequency_penalty: float = 0.1
    top_p: float = 0.95
    connect_timeout_s: float = 10.0
    read_timeout_s: float = 30.0
    
    # Adaptive length
    enable_adaptive_length: bool = True
    short_response_triggers: List[str] = field(
        default_factory=lambda: ["yes", "no", "thanks", "ok", "sure", "hi", "hello"]
    )
    short_response_max_tokens: int = 80


@dataclass
class GenerationResult:
    """Result of LLM generation."""
    content: str
    tokens_generated: int
    generation_time_ms: float
    finish_reason: str
    was_cancelled: bool = False


class AsyncLLMStream:
    """
    Async streaming LLM client with Azure OpenAI.

    Features:
    - Streaming token delivery
    - Mid-generation cancellation
    - Single retry on failure
    - Event publishing

    Usage:
        llm = AsyncLLMStream(event_bus)
        async for token in llm.generate_stream(messages):
            print(token, end="", flush=True)
    """

    def __init__(
        self,
        event_bus: EventBus,
        config: Optional[GenerationConfig] = None,
    ):
        self._event_bus = event_bus
        self._config = config or GenerationConfig(
            temperature=settings.llm.temperature,
            max_tokens=settings.llm.max_tokens,
            presence_penalty=settings.llm.presence_penalty,
            frequency_penalty=settings.llm.frequency_penalty,
        )

        # Azure OpenAI settings
        self._api_key = settings.azure.api_key
        self._endpoint = settings.azure.endpoint
        self._deployment = settings.azure.chat_deployment
        self._api_version = settings.azure.api_version

        # State
        self._state = GenerationState.IDLE
        self._cancel_event = asyncio.Event()
        self._current_generation_id = ""

        # Metrics
        self._total_tokens = 0
        self._generation_count = 0

    @property
    def _url(self) -> str:
        """Get Azure OpenAI chat completion URL."""
        base = self._endpoint.rstrip("/")
        return (
            f"{base}/openai/deployments/{self._deployment}"
            f"/chat/completions?api-version={self._api_version}"
        )

    @property
    def _headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            "api-key": self._api_key,
            "Content-Type": "application/json",
        }

    async def generate_stream(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        Generate streaming response from LLM.

        Args:
            messages: Conversation messages
            temperature: Override temperature
            max_tokens: Override max tokens

        Yields:
            Generated tokens one at a time
        """
        # Try with retry
        last_error = None
        for attempt in range(2):
            try:
                async for token in self._generate_stream_impl(
                    messages, temperature, max_tokens
                ):
                    yield token
                return
            except asyncio.CancelledError:
                raise
            except Exception as e:
                last_error = e
                if attempt == 0:
                    logger.warning(f"LLM error (attempt 1/2): {e}, retrying...")
                    await asyncio.sleep(0.3)
                else:
                    logger.error(f"LLM error (attempt 2/2): {e}")
                    raise

        if last_error:
            raise last_error

    async def _generate_stream_impl(
        self,
        messages: List[Message],
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> AsyncIterator[str]:
        """Internal streaming implementation."""
        self._current_generation_id = f"gen_{uuid.uuid4().hex[:8]}"
        self._cancel_event.clear()
        self._state = GenerationState.GENERATING

        # Adaptive max tokens
        if self._config.enable_adaptive_length and max_tokens is None:
            max_tokens = self._compute_adaptive_length(messages)
        
        max_tokens = max_tokens or self._config.max_tokens

        body = {
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature or self._config.temperature,
            "max_tokens": max_tokens,
            "presence_penalty": self._config.presence_penalty,
            "frequency_penalty": self._config.frequency_penalty,
            "top_p": self._config.top_p,
            "stream": True,
        }

        start_time = time.time()
        token_count = 0
        accumulated = ""

        timeout = aiohttp.ClientTimeout(
            total=self._config.read_timeout_s,
            connect=self._config.connect_timeout_s,
        )

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self._url,
                    headers=self._headers,
                    json=body,
                ) as response:
                    response.raise_for_status()

                    async for line in response.content:
                        if self._cancel_event.is_set():
                            self._state = GenerationState.CANCELLED
                            break

                        line = line.decode("utf-8").strip()
                        if not line or not line.startswith("data: "):
                            continue

                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                finish_reason = choices[0].get("finish_reason")

                                if content:
                                    token_count += 1
                                    accumulated += content

                                    # Publish token event
                                    await self._event_bus.publish(
                                        LLMTokenEvent(
                                            token=content,
                                            token_index=token_count,
                                            is_first=(token_count == 1),
                                            is_last=False,
                                            accumulated_text=accumulated,
                                            generation_id=self._current_generation_id,
                                        )
                                    )
                                    yield content

                                if finish_reason:
                                    await self._event_bus.publish(
                                        LLMTokenEvent(
                                            token="",
                                            token_index=token_count,
                                            is_first=False,
                                            is_last=True,
                                            accumulated_text=accumulated,
                                            finish_reason=finish_reason,
                                            generation_id=self._current_generation_id,
                                        )
                                    )

                        except json.JSONDecodeError:
                            continue

            self._state = GenerationState.COMPLETED

        finally:
            generation_time = (time.time() - start_time) * 1000
            self._total_tokens += token_count
            self._generation_count += 1
            logger.debug(
                f"Generated {token_count} tokens in {generation_time:.0f}ms"
            )

    def _compute_adaptive_length(self, messages: List[Message]) -> int:
        """Compute adaptive max tokens based on user input."""
        user_messages = [m for m in messages if m.role == "user"]
        if not user_messages:
            return self._config.max_tokens

        last_user = user_messages[-1].content.lower()
        word_count = len(last_user.split())

        # Very short inputs
        if word_count <= 3:
            for trigger in self._config.short_response_triggers:
                if trigger in last_user:
                    return self._config.short_response_max_tokens

        # Short queries
        if word_count <= 10:
            return min(self._config.max_tokens, 200)

        return self._config.max_tokens

    async def generate(self, messages: List[Message], **kwargs) -> GenerationResult:
        """Generate complete response (non-streaming wrapper)."""
        start_time = time.time()
        content = ""
        token_count = 0
        finish_reason = ""

        try:
            async for token in self.generate_stream(messages, **kwargs):
                content += token
                token_count += 1
            finish_reason = "stop"
        except asyncio.CancelledError:
            finish_reason = "cancelled"

        return GenerationResult(
            content=content,
            tokens_generated=token_count,
            generation_time_ms=(time.time() - start_time) * 1000,
            finish_reason=finish_reason,
            was_cancelled=(finish_reason == "cancelled"),
        )

    async def cancel(self) -> None:
        """Cancel current generation."""
        if self._state == GenerationState.GENERATING:
            self._cancel_event.set()
            self._state = GenerationState.CANCELLED
            logger.debug("Generation cancelled")

    async def handle_barge_in(self, event: BargeInEvent) -> None:
        """Handle barge-in by cancelling generation."""
        await self.cancel()

    async def close(self) -> None:
        """Cleanup resources."""
        await self.cancel()

    @property
    def state(self) -> GenerationState:
        """Get current state."""
        return self._state

    @property
    def is_generating(self) -> bool:
        """Check if currently generating."""
        return self._state == GenerationState.GENERATING

    @property
    def stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        return {
            "total_tokens": self._total_tokens,
            "generation_count": self._generation_count,
            "avg_tokens": (
                self._total_tokens / self._generation_count
                if self._generation_count > 0 else 0
            ),
        }


class MicroResponseGenerator:
    """
    Generates quick micro-responses without LLM call.

    Used for:
    - Back-channels ("Mm-hmm", "I see")
    - Acknowledgements ("Got it", "Sure")
    """

    BACKCHANNELS = ["Mm-hmm", "I see", "Right", "Okay"]
    ACKNOWLEDGEMENTS = ["Got it", "Sure thing", "Absolutely", "Of course"]
    THINKING = ["Let me check that", "One moment", "Let me look into that"]

    def __init__(self):
        self._indices = {
            "backchannel": 0,
            "acknowledgement": 0,
            "thinking": 0,
        }

    def get_response(self, category: str) -> str:
        """Get next response from category."""
        responses = {
            "backchannel": self.BACKCHANNELS,
            "acknowledgement": self.ACKNOWLEDGEMENTS,
            "thinking": self.THINKING,
        }.get(category, self.ACKNOWLEDGEMENTS)

        idx = self._indices.get(category, 0)
        response = responses[idx % len(responses)]
        self._indices[category] = idx + 1

        return response

    def get_backchannel(self) -> str:
        return self.get_response("backchannel")

    def get_acknowledgement(self) -> str:
        return self.get_response("acknowledgement")

    def get_thinking(self) -> str:
        return self.get_response("thinking")
