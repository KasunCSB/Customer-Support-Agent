"""
RAG Pipeline Module

This module provides the complete RAG (Retrieval-Augmented Generation) pipeline
that orchestrates document retrieval and LLM response generation.

Architecture:
- RAGPipeline: Main orchestrator class
- Integrates Retriever for context finding
- Integrates LLM for response generation
- Supports conversation history for multi-turn chat

SOLID Principles:
- Single Responsibility: Orchestrates RAG flow only
- Dependency Inversion: Depends on abstractions (Retriever, LLM)
- Open/Closed: Pipeline behavior extensible via configuration

Usage:
    from src.pipeline.rag_pipeline import RAGPipeline
    
    pipeline = RAGPipeline()
    response = pipeline.query("How do I reset my password?")
    print(response.answer)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime
import threading

from src.core.embeddings import EmbeddingProvider, AzureEmbeddingProvider
from src.core.vectorstore import VectorStore, ChromaVectorStore
from src.core.llm import (
    LLMProvider, AzureLLMProvider, Message,
    build_rag_messages, RAG_SYSTEM_PROMPT
)
from src.pipeline.retriever import Retriever, RetrievalResult
from src.config import settings
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RAGResponse:
    """
    Response from the RAG pipeline.
    
    Attributes:
        answer: Generated answer text
        query: Original query
        sources: List of source documents used
        retrieval_result: Full retrieval result for inspection
        model: Model used for generation
        tokens_used: Token usage statistics
        timestamp: When response was generated
    """
    answer: str
    query: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    retrieval_result: Optional[RetrievalResult] = None
    model: str = ""
    tokens_used: Dict[str, int] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def has_sources(self) -> bool:
        """Check if sources were found and used."""
        return len(self.sources) > 0
    
    def format_with_sources(self) -> str:
        """Format answer with source citations."""
        if not self.sources:
            return self.answer
        
        sources_text = "\n\n**Sources:**\n"
        for i, src in enumerate(self.sources, 1):
            source_name = src.get("source", "Unknown")
            sources_text += f"- {source_name}\n"
        
        return self.answer + sources_text


class ConversationMemory:
    """
    Simple conversation memory for multi-turn chat.
    
    Stores recent messages and provides them as context
    for follow-up questions.
    
    Attributes:
        max_turns: Maximum conversation turns to remember
        messages: List of conversation messages
    """
    
    def __init__(self, max_turns: int = 5):
        """
        Initialize conversation memory.
        
        Args:
            max_turns: Maximum turns to keep in memory
        """
        self.max_turns = max_turns
        self.messages: List[Message] = []
    
    def add_turn(self, user_message: str, assistant_message: str) -> None:
        """
        Add a conversation turn.
        
        Args:
            user_message: User's message
            assistant_message: Assistant's response
        """
        self.messages.append(Message(role="user", content=user_message))
        self.messages.append(Message(role="assistant", content=assistant_message))
        
        # Trim to max turns (each turn = 2 messages)
        max_messages = self.max_turns * 2
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages:]
    
    def get_history(self) -> List[Message]:
        """Get conversation history messages."""
        return self.messages.copy()
    
    def clear(self) -> None:
        """Clear conversation history."""
        self.messages.clear()


class RAGPipeline:
    """
    Complete RAG pipeline for question answering.
    
    Orchestrates:
    1. Query processing
    2. Document retrieval
    3. Context assembly
    4. LLM response generation
    5. Source citation
    
    Features:
    - Configurable retrieval parameters
    - Conversation memory for follow-ups
    - Streaming response support
    - Token budget management
    
    Example:
        pipeline = RAGPipeline()
        
        # Simple query
        response = pipeline.query("How do I reset my password?")
        print(response.answer)
        
        # With conversation memory
        pipeline.chat("What about two-factor auth?")  # Follow-up
        
        # Streaming response
        for token in pipeline.stream_query("Tell me about returns"):
            print(token, end="", flush=True)
    """
    
    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        vector_store: Optional[VectorStore] = None,
        llm_provider: Optional[LLMProvider] = None,
        retriever: Optional[Retriever] = None,
        system_prompt: Optional[str] = None,
        enable_memory: bool = True,
        memory_turns: int = 5
    ):
        """
        Initialize the RAG pipeline.
        
        Args:
            embedding_provider: Provider for embeddings (defaults to Azure)
            vector_store: Vector store for documents (defaults to Chroma)
            llm_provider: LLM for generation (defaults to Azure)
            retriever: Pre-configured retriever (optional)
            system_prompt: Custom system prompt
            enable_memory: Enable conversation memory
            memory_turns: Number of turns to remember
        """
        # Initialize components with defaults
        self.embedding_provider = embedding_provider or AzureEmbeddingProvider()
        self.vector_store = vector_store or ChromaVectorStore()
        self.llm_provider = llm_provider or AzureLLMProvider()
        
        # Initialize retriever
        self.retriever = retriever or Retriever(
            embedding_provider=self.embedding_provider,
            vector_store=self.vector_store
        )
        
        # Configuration
        self.system_prompt = system_prompt or RAG_SYSTEM_PROMPT
        self.context_token_budget = settings.retrieval.context_token_budget
        
        # Conversation memory (session-aware)
        self._memory_enabled = enable_memory
        self._memory_turns = memory_turns
        self._default_memory = ConversationMemory(max_turns=memory_turns) if enable_memory else None
        self._session_memories: Dict[str, ConversationMemory] = {}
        self._memory_lock = threading.Lock()
        
        logger.info(
            f"Initialized RAGPipeline: "
            f"memory={'enabled' if enable_memory else 'disabled'}, "
            f"context_budget={self.context_token_budget}"
        )

    def _get_memory(self, session_id: Optional[str]) -> Optional[ConversationMemory]:
        """Get (or create) the conversation memory buffer for a session."""
        if not self._memory_enabled:
            return None

        if not session_id:
            return self._default_memory

        with self._memory_lock:
            mem = self._session_memories.get(session_id)
            if mem is None:
                mem = ConversationMemory(max_turns=self._memory_turns)
                self._session_memories[session_id] = mem
            return mem
    
    def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        include_history: bool = False,
        filter_metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> RAGResponse:
        """
        Process a question through the RAG pipeline.
        
        Args:
            question: User's question
            top_k: Number of documents to retrieve
            include_history: Include conversation history in context
            filter_metadata: Filter retrieval by metadata
            
        Returns:
            RAGResponse with answer and sources
        """
        logger.info(f"Processing query: {question[:50]}...")
        
        # Step 1: Retrieve relevant documents
        retrieval_result = self.retriever.retrieve(
            query=question,
            top_k=top_k,
            filter_metadata=filter_metadata
        )
        
        # Step 2: Format context
        context = retrieval_result.format_context(
            include_source=True,
            max_tokens=self.context_token_budget
        )
        
        if not context:
            context = "No relevant information found in the knowledge base."
        
        # Step 3: Build messages
        memory = self._get_memory(session_id)
        history = memory.get_history() if (memory and include_history) else None
        messages = build_rag_messages(
            question=question,
            context=context,
            system_prompt=self.system_prompt,
            conversation_history=history
        )
        
        # Step 4: Generate response
        chat_response = self.llm_provider.chat(messages)
        
        # Step 5: Build response
        response = RAGResponse(
            answer=chat_response.content,
            query=question,
            sources=retrieval_result.get_sources(),
            retrieval_result=retrieval_result,
            model=chat_response.model,
            tokens_used=chat_response.usage
        )
        
        # Step 6: Update memory
        if memory:
            memory.add_turn(question, chat_response.content)
        
        logger.info(
            f"Generated response: {len(response.answer)} chars, "
            f"{len(response.sources)} sources, "
            f"{chat_response.total_tokens} tokens"
        )
        
        return response
    
    def chat(
        self,
        message: str,
        top_k: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> RAGResponse:
        """
        Send a message in conversational mode.
        
        Includes conversation history for context-aware responses.
        
        Args:
            message: User's message
            top_k: Number of documents to retrieve
            
        Returns:
            RAGResponse with answer
        """
        return self.query(message, top_k=top_k, include_history=True, session_id=session_id)
    
    def stream_query(
        self,
        question: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
        include_history: bool = True,
        session_id: Optional[str] = None
    ) -> Iterator[str]:
        """
        Stream a response token by token.
        
        Args:
            question: User's question
            top_k: Number of documents to retrieve
            filter_metadata: Filter retrieval by metadata
            include_history: Include conversation history
            
        Yields:
            Response tokens as they're generated
        """
        logger.info(f"Streaming query: {question[:50]}...")
        
        # Retrieve and prepare context
        retrieval_result = self.retriever.retrieve(
            query=question,
            top_k=top_k,
            filter_metadata=filter_metadata
        )
        
        context = retrieval_result.format_context(
            include_source=True,
            max_tokens=self.context_token_budget
        )
        
        if not context:
            context = "No relevant information found in the knowledge base."
        
        # Build messages with conversation history
        memory = self._get_memory(session_id)
        history = memory.get_history() if (memory and include_history) else None
        messages = build_rag_messages(
            question=question,
            context=context,
            system_prompt=self.system_prompt,
            conversation_history=history
        )
        
        # Stream response
        full_response = ""
        for token in self.llm_provider.stream_chat(messages):
            full_response += token
            yield token
        
        # Update memory after streaming completes
        if memory:
            memory.add_turn(question, full_response)
    
    def clear_memory(self, session_id: Optional[str] = None) -> None:
        """Clear conversation memory (optionally for a single session)."""
        if not self._memory_enabled:
            return

        if session_id:
            with self._memory_lock:
                mem = self._session_memories.get(session_id)
                if mem:
                    mem.clear()
            logger.info(f"Cleared conversation memory for session {session_id}")
            return

        # Clear all memories
        if self._default_memory:
            self._default_memory.clear()
        with self._memory_lock:
            for mem in self._session_memories.values():
                mem.clear()
        logger.info("Cleared conversation memory")
    
    @property
    def document_count(self) -> int:
        """Get number of documents in the vector store."""
        return self.vector_store.count()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics.
        
        Returns:
            Dictionary with pipeline stats
        """
        return {
            "document_count": self.document_count,
            "memory_enabled": self._memory_enabled,
            "memory_turns": len(self._default_memory.messages) // 2 if self._default_memory else 0,
            "context_token_budget": self.context_token_budget
        }
