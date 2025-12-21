"""
Real-Time RAG Engine Module

Provides async retrieval with:
- Intent-based RAG triggering
- Session-level result caching
- Simple error handling

Designed for stability without complex speculative retrieval.
"""

import asyncio
import time
import hashlib
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, List, Dict, Any, Tuple
from collections import OrderedDict

from src.config import settings
from src.logger import get_logger
from src.core.embeddings import AzureEmbeddingProvider
from src.core.vectorstore import ChromaVectorStore
from .events import (
    EventBus,
    IntentEvent,
    IntentConfidence,
    RetrievalEvent,
)

logger = get_logger(__name__)


class RetrievalState(Enum):
    """State of retrieval operation."""
    IDLE = auto()
    RETRIEVING = auto()
    COMPLETE = auto()


@dataclass
class RetrievalConfig:
    """Configuration for RAG."""
    top_k: int = 3
    enable_cache: bool = True
    cache_size: int = 50
    cache_ttl_seconds: float = 300
    max_context_tokens: int = 2000


@dataclass
class RetrievalResult:
    """Result from RAG retrieval."""
    documents: List[Dict[str, Any]]
    query: str
    retrieval_time_ms: float
    cache_hit: bool

    def format_context(
        self,
        max_tokens: int = 2000,
        include_source: bool = True,
    ) -> str:
        """Format documents as LLM context."""
        if not self.documents:
            return ""

        parts = []
        for i, doc in enumerate(self.documents):
            text = doc.get("text", "")
            if include_source:
                source = doc.get("metadata", {}).get("source", "Knowledge Base")
                parts.append(f"[{i + 1}. {source}]\n{text}")
            else:
                parts.append(text)

        context = "\n\n---\n\n".join(parts)

        max_chars = max_tokens * 4
        if len(context) > max_chars:
            context = context[:max_chars] + "..."

        return context

    @property
    def has_results(self) -> bool:
        return len(self.documents) > 0


class LRUCache:
    """Simple LRU cache for retrieval results."""

    def __init__(self, max_size: int = 50, ttl_seconds: float = 300):
        self._cache: OrderedDict[str, Tuple[float, Any]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds

    def _make_key(self, query: str, top_k: int) -> str:
        """Create cache key from query."""
        normalized = query.lower().strip()
        return hashlib.md5(f"{normalized}:{top_k}".encode()).hexdigest()

    def get(self, query: str, top_k: int) -> Optional[Any]:
        """Get cached result if exists and not expired."""
        key = self._make_key(query, top_k)

        if key not in self._cache:
            return None

        timestamp, value = self._cache[key]

        if time.time() - timestamp > self._ttl:
            del self._cache[key]
            return None

        self._cache.move_to_end(key)
        return value

    def set(self, query: str, top_k: int, value: Any) -> None:
        """Cache a result."""
        key = self._make_key(query, top_k)

        while len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)

        self._cache[key] = (time.time(), value)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


class RealtimeRAGEngine:
    """
    Real-time RAG engine with caching.

    Features:
    - Intent-triggered retrieval
    - Session-level caching
    - Simple error handling

    Usage:
        rag = RealtimeRAGEngine(event_bus)
        await rag.start()
        # Responds to IntentEvent and emits RetrievalEvent
    """

    def __init__(
        self,
        event_bus: EventBus,
        config: Optional[RetrievalConfig] = None,
        embedding_provider: Optional[AzureEmbeddingProvider] = None,
        vector_store: Optional[ChromaVectorStore] = None,
    ):
        self._event_bus = event_bus
        self._config = config or RetrievalConfig(
            top_k=settings.retrieval.top_k,
            max_context_tokens=settings.retrieval.context_token_budget,
        )

        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

        self._state = RetrievalState.IDLE
        self._cache = LRUCache(
            max_size=self._config.cache_size,
            ttl_seconds=self._config.cache_ttl_seconds,
        )

        # Metrics
        self._total_retrievals = 0
        self._cache_hits = 0

    def _ensure_providers(self) -> None:
        """Lazily initialize providers."""
        if self._embedding_provider is None:
            self._embedding_provider = AzureEmbeddingProvider()
        if self._vector_store is None:
            self._vector_store = ChromaVectorStore()

    async def start(self) -> None:
        """Start RAG engine."""
        # Initialize providers eagerly at startup to avoid timeout on first query
        self._ensure_providers()
        self._event_bus.subscribe(IntentEvent, self._handle_intent)
        logger.info("RAG engine started")

    async def stop(self) -> None:
        """Stop RAG engine."""
        self._event_bus.unsubscribe(IntentEvent, self._handle_intent)
        logger.info("RAG engine stopped")

    async def _handle_intent(self, event: IntentEvent) -> None:
        """Handle intent event and trigger retrieval."""
        if event.cancelled or not event.requires_retrieval:
            logger.debug(f"Intent skipped: cancelled={event.cancelled}, requires_retrieval={event.requires_retrieval}")
            return

        # Only retrieve on confirmed or likely intents
        if event.confidence == IntentConfidence.SPECULATIVE:
            logger.debug("Intent skipped: speculative confidence")
            return

        query = event.transcript_text or " ".join(event.keywords)
        if not query:
            logger.debug("Intent skipped: no query text")
            return
        
        logger.info(f"RAG triggered for query: '{query[:50]}...'")
        
        # Run retrieval in background to avoid blocking event bus
        asyncio.create_task(self._run_retrieval(query))
    
    async def _run_retrieval(self, query: str) -> None:
        """Run retrieval in background task."""
        try:
            # Apply timeout to the actual retrieval operation
            logger.debug("Starting RAG retrieve with 25s timeout...")
            result = await asyncio.wait_for(
                self.retrieve(query),
                timeout=25.0  # 25 second timeout for retrieval
            )
            logger.debug("RAG retrieve completed successfully")

            await self._event_bus.publish(
                RetrievalEvent(
                    query=query,
                    documents=result.documents,
                    retrieval_time_ms=result.retrieval_time_ms,
                    cache_hit=result.cache_hit,
                )
            )
        except asyncio.TimeoutError:
            logger.error(f"RAG RETRIEVAL TIMEOUT after 25s for query: '{query[:50]}...'")
            logger.error("Publishing empty RetrievalEvent due to timeout")
            # Emit empty result on timeout
            await self._event_bus.publish(
                RetrievalEvent(query=query, documents=[])
            )
        except Exception as e:
            logger.error(f"RAG retrieval error: {e}")
            # Emit empty result on error
            await self._event_bus.publish(
                RetrievalEvent(query=query, documents=[])
            )

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> RetrievalResult:
        """
        Retrieve relevant documents for query.

        Args:
            query: Search query
            top_k: Number of results

        Returns:
            RetrievalResult with documents
        """
        top_k = top_k or self._config.top_k
        self._state = RetrievalState.RETRIEVING
        start_time = time.time()
        logger.debug(f"RAG retrieve() started for: '{query[:50]}...'")

        try:
            # Check cache
            if self._config.enable_cache:
                cached = self._cache.get(query, top_k)
                if cached is not None:
                    self._cache_hits += 1
                    retrieval_time = (time.time() - start_time) * 1000
                    logger.debug(f"Cache hit for: {query[:30]}...")
                    return RetrievalResult(
                        documents=cached,
                        query=query,
                        retrieval_time_ms=retrieval_time,
                        cache_hit=True,
                    )

            # Ensure providers are initialized
            init_start = time.time()
            self._ensure_providers()
            init_time = (time.time() - init_start) * 1000
            if init_time > 10:
                logger.debug(f"Provider init took: {init_time:.0f}ms")

            # Get embedding (using embed method, not embed_query)
            embed_start = time.time()
            embedding = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._embedding_provider.embed(query)  # type: ignore
            )
            embed_time = (time.time() - embed_start) * 1000
            logger.debug(f"Query embedding took: {embed_time:.0f}ms")

            # Search vector store
            search_start = time.time()
            search_results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._vector_store.search(embedding, top_k=top_k)  # type: ignore
            )
            search_time = (time.time() - search_start) * 1000
            logger.debug(f"Vector search took: {search_time:.0f}ms")

            # Format results (SearchResults contains SearchResult objects)
            documents = []
            for result in search_results:
                doc = {
                    "text": result.text,
                    "metadata": result.metadata,
                    "score": result.score,
                }
                documents.append(doc)

            # Cache results
            if self._config.enable_cache:
                self._cache.set(query, top_k, documents)

            retrieval_time = (time.time() - start_time) * 1000
            self._total_retrievals += 1

            # Warn if retrieval is taking too long
            if retrieval_time > 10000:
                logger.warning(
                    f"Very slow RAG retrieval: {retrieval_time:.0f}ms for '{query[:50]}...'"
                )
            elif retrieval_time > 5000:
                logger.info(
                    f"Slow RAG retrieval: {retrieval_time:.0f}ms for '{query[:50]}...'"
                )
            else:
                logger.debug(
                    f"Retrieved {len(documents)} docs for '{query[:30]}...' "
                    f"in {retrieval_time:.0f}ms"
                )

            return RetrievalResult(
                documents=documents,
                query=query,
                retrieval_time_ms=retrieval_time,
                cache_hit=False,
            )

        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return RetrievalResult(
                documents=[],
                query=query,
                retrieval_time_ms=(time.time() - start_time) * 1000,
                cache_hit=False,
            )
        finally:
            self._state = RetrievalState.COMPLETE

    @property
    def state(self) -> RetrievalState:
        """Get current state."""
        return self._state

    @property
    def stats(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        return {
            "total_retrievals": self._total_retrievals,
            "cache_hits": self._cache_hits,
            "cache_size": self._cache.size,
            "cache_hit_rate": (
                self._cache_hits / max(self._total_retrievals, 1) * 100
            ),
        }
