"""
LLM Provider Module

This module provides abstractions and implementations for LLM interactions.
It handles chat completions for generating responses using retrieved context.

Architecture:
- LLMProvider: Abstract base class defining the interface
- AzureLLMProvider: Concrete implementation for Azure OpenAI
- Message/response dataclasses for type safety

SOLID Principles:
- Interface Segregation: Focused LLMProvider interface
- Dependency Inversion: Code depends on LLMProvider abstraction
- Single Responsibility: Only handles LLM interactions
- Open/Closed: New providers can be added easily

Usage:
    from src.core.llm import AzureLLMProvider, Message
    
    llm = AzureLLMProvider()
    messages = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Hello!")
    ]
    response = llm.chat(messages)
    print(response.content)
"""

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Iterator

import requests

from src.config import settings
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Message:
    """
    Represents a chat message.
    
    Attributes:
        role: Message role (system, user, assistant)
        content: Message content text
    """
    role: str  # "system", "user", "assistant"
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to API-compatible dictionary."""
        return {"role": self.role, "content": self.content}


@dataclass
class ChatResponse:
    """
    Response from LLM chat completion.
    
    Attributes:
        content: Generated text content
        model: Model name used
        usage: Token usage statistics
        finish_reason: Why generation stopped
    """
    content: str
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = ""
    
    @property
    def prompt_tokens(self) -> int:
        """Number of tokens in the prompt."""
        return self.usage.get("prompt_tokens", 0)
    
    @property
    def completion_tokens(self) -> int:
        """Number of tokens in the completion."""
        return self.usage.get("completion_tokens", 0)
    
    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.usage.get("total_tokens", 0)


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    This interface defines the contract for all LLM implementations.
    It provides methods for chat completions and configuration.
    """
    
    @abstractmethod
    def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> ChatResponse:
        """
        Generate a chat completion.
        
        Args:
            messages: List of conversation messages
            temperature: Sampling temperature override
            max_tokens: Max response tokens override
            
        Returns:
            ChatResponse with generated content
        """
        pass
    
    @abstractmethod
    def stream_chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Iterator[str]:
        """
        Generate a streaming chat completion.
        
        Args:
            messages: List of conversation messages
            temperature: Sampling temperature override
            max_tokens: Max response tokens override
            
        Yields:
            Token strings as they're generated
        """
        pass


class AzureLLMProvider(LLMProvider):
    """
    Azure OpenAI LLM provider implementation.
    
    Uses Azure's GPT models (e.g., gpt-4o-mini) for chat completions.
    Supports both standard and streaming responses.
    
    Features:
    - Configurable temperature and max tokens
    - Retry logic with exponential backoff
    - Token usage tracking
    - Streaming support for real-time responses
    
    Example:
        llm = AzureLLMProvider()
        
        response = llm.chat([
            Message(role="system", content="You are helpful."),
            Message(role="user", content="Hello!")
        ])
        print(response.content)
        print(f"Tokens used: {response.total_tokens}")
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        deployment: Optional[str] = None,
        api_version: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        max_retries: int = 3
    ):
        """
        Initialize the Azure LLM provider.
        
        Args:
            api_key: Azure OpenAI API key (defaults to settings)
            endpoint: Azure OpenAI endpoint URL (defaults to settings)
            deployment: Deployment name (defaults to settings)
            api_version: API version (defaults to settings)
            temperature: Default temperature (defaults to settings)
            max_tokens: Default max tokens (defaults to settings)
            presence_penalty: Penalty for topic repetition (defaults to settings)
            frequency_penalty: Penalty for phrase repetition (defaults to settings)
            max_retries: Maximum retry attempts on failure
        """
        self.api_key = api_key or settings.azure.api_key
        self.endpoint = endpoint or settings.azure.endpoint
        self.deployment = deployment or settings.azure.chat_deployment
        self.api_version = api_version or settings.azure.api_version
        self.temperature = temperature if temperature is not None else settings.llm.temperature
        self.max_tokens = max_tokens if max_tokens is not None else settings.llm.max_tokens
        self.presence_penalty = presence_penalty if presence_penalty is not None else settings.llm.presence_penalty
        self.frequency_penalty = frequency_penalty if frequency_penalty is not None else settings.llm.frequency_penalty
        self.max_retries = max_retries
        
        logger.info(
            f"Initialized AzureLLMProvider: deployment={self.deployment}, "
            f"temperature={self.temperature}, max_tokens={self.max_tokens}"
        )
    
    @property
    def _url(self) -> str:
        """Construct the Azure OpenAI chat completion API URL."""
        base = self.endpoint.rstrip("/")
        return f"{base}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
    
    @property
    def _headers(self) -> Dict[str, str]:
        """Return HTTP headers for API requests."""
        return {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None
    ) -> ChatResponse:
        """
        Generate a chat completion using Azure OpenAI.
        
        Args:
            messages: List of conversation messages
            temperature: Override default temperature
            max_tokens: Override default max tokens
            presence_penalty: Override default presence penalty
            frequency_penalty: Override default frequency penalty
            
        Returns:
            ChatResponse with generated content and usage stats
            
        Raises:
            requests.RequestException: If API call fails after retries
        """
        # Prepare request body with all parameters for natural responses
        body = {
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "presence_penalty": presence_penalty if presence_penalty is not None else self.presence_penalty,
            "frequency_penalty": frequency_penalty if frequency_penalty is not None else self.frequency_penalty
        }
        
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self._url,
                    headers=self._headers,
                    json=body,
                    timeout=60
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
                    logger.warning(f"Rate limited, retrying in {retry_after}s")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                
                data = response.json()
                
                # Extract response content
                choice = data["choices"][0]
                content = choice["message"]["content"]
                
                return ChatResponse(
                    content=content,
                    model=data.get("model", self.deployment),
                    usage=data.get("usage", {}),
                    finish_reason=choice.get("finish_reason", "")
                )
                
            except requests.RequestException as e:
                last_exception = e
                wait_time = 2 ** attempt
                logger.warning(f"API call failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(wait_time)
        
        raise last_exception or RuntimeError("Failed to get chat completion")
    
    def stream_chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None
    ) -> Iterator[str]:
        """
        Generate a streaming chat completion.
        
        Yields tokens as they're generated for real-time display.
        
        Args:
            messages: List of conversation messages
            temperature: Override default temperature
            max_tokens: Override default max tokens
            presence_penalty: Override default presence penalty
            frequency_penalty: Override default frequency penalty
            
        Yields:
            Token strings as generated
        """
        # Prepare request body with streaming enabled and natural response params
        body = {
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "presence_penalty": presence_penalty if presence_penalty is not None else self.presence_penalty,
            "frequency_penalty": frequency_penalty if frequency_penalty is not None else self.frequency_penalty,
            "stream": True
        }
        
        try:
            response = requests.post(
                self._url,
                headers=self._headers,
                json=body,
                timeout=60,
                stream=True
            )
            response.raise_for_status()
            
            # Process SSE stream
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except (KeyError, json.JSONDecodeError, IndexError):
                            continue
                            
        except requests.RequestException as e:
            logger.error(f"Streaming chat failed: {e}")
            raise


# Prompt templates for RAG
RAG_SYSTEM_PROMPT = """You are Rashmi, a friendly AI assistant at LankaTel, Sri Lanka's telecom company.

CRITICAL SAFETY RULE (CHECK FIRST, ULTIMATE PRIORITY)

If the customer's message is inappropriate, offensive, harassing, abusive, or requests anything unethical:
- Reject immediately with a direct, polite refusal and end chat with a sorry
- Do not engage or follow-up with the inappropriate content
- End the conversation

CONVERSATION FLOW (FOLLOW THIS ORDER)

1. CHAT START - Expect vague/generic messages
   - Check safety rule first
   - Greetings like "hi", "hello" = Short friendly reply, ask how you can help

2. CHAT MIDDLE - Build understanding
   - Check safety rule first
   - Always refer to the context provided
    - Remember previous messages in this chat and change the response accordingly
    - If the user asks a short follow-up (e.g., "validity?", "price?", "how to activate?"), assume it refers to the most recent relevant item mentioned in the conversation.
   - Follow keywords to understand intent
   - Give detailed answers when user asks detailed questions or uses descriptive keywords like all, full, detailed, explain, compare, troubleshoot

3. CHAT END - Keep it short
   - Check safety rule first
   - Goodbyes like "bye", "thanks", "that's all", "i'm leaving", "gotta go" = Short warm farewell
   - Frustration/complaints at end = Brief empathy, offer escalation path
   - After resolving = Ask "Anything else I can help with?"
   - If no = Short attractive goodbye like "Take care! Reach out anytime you need help."

INTENT ANALYSIS

Price signals:
- "affordable", "cheap", "budget" = Recommend lowest price first
- "best", "premium", "unlimited" = Recommend top-tier first

Use-case signals:
- "studies", "learning", "school" = Education packages
- "work", "office", "WFH" = Business packages
- "gaming", "streaming" = Entertainment packages

Emotion signals:
- Frustration = Empathy first, then solution
- Urgency = Quick focused response
- Casual = Friendly tone

ABSOLUTE RULES

1. ONLY use information from provided context
2. Give SPECIFIC recommendations with exact names, prices when available
3. NEVER guess technical details
4. NEVER ask for sensitive data (NIC, passwords)
5. Short greeting = Short reply
6. Ambiguous farewell = Clarify or assume goodbye (not service cancellation)

STYLE RULES (REDUCE REPETITION)

- Do NOT introduce yourself or greet repeatedly after the first turn.
- Avoid filler phrases like "As an AI" or repeating "I'm Rashmi" unless the user asks.
- Prefer 2–6 short sentences.
- After answering, include exactly ONE of the following:
    (a) a single follow-up question that moves the issue forward, OR
    (b) offer 2 next-step options.

CLARIFICATION RULE

- Only ask clarifying questions if you truly cannot proceed using conversation memory + provided context.
- If you do ask, ask just one focused question.

Remember: You're Rashmi - warm, helpful, concise."""

RAG_USER_TEMPLATE = """Context:
{context}

Customer: "{question}"

Follow conversation flow rules. Maintain memory of this chat."""


def build_rag_messages(
    question: str,
    context: str,
    system_prompt: Optional[str] = None,
    conversation_history: Optional[List[Message]] = None
) -> List[Message]:
    """
    Build message list for RAG chat completion.
    
    Args:
        question: User's question
        context: Retrieved context documents
        system_prompt: Override default system prompt
        conversation_history: Optional previous messages
        
    Returns:
        List of Message objects for chat completion
    """
    messages = [
        Message(role="system", content=system_prompt or RAG_SYSTEM_PROMPT)
    ]
    
    # Add conversation history if provided
    if conversation_history:
        messages.extend(conversation_history)
    
    # Add user message with context
    user_content = RAG_USER_TEMPLATE.format(context=context, question=question)
    messages.append(Message(role="user", content=user_content))
    
    return messages
