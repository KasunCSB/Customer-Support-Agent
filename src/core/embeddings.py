"""
Embedding Provider Module

This module provides abstractions and implementations for text embedding generation.
It converts text into high-dimensional vectors that capture semantic meaning.

Architecture:
- EmbeddingProvider: Abstract base class defining the interface (ISP)
- AzureEmbeddingProvider: Concrete implementation for Azure OpenAI
- Caching support for cost optimization

SOLID Principles:
- Interface Segregation: Small, focused EmbeddingProvider interface
- Dependency Inversion: Code depends on EmbeddingProvider abstraction
- Single Responsibility: Only handles embedding generation
- Open/Closed: New providers can be added without modifying existing code

Usage:
    from src.core.embeddings import AzureEmbeddingProvider
    
    provider = AzureEmbeddingProvider()
    vectors = provider.embed_batch(["Hello world", "How are you?"])
"""

import hashlib
import json
import math
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any

import requests

from src.config import settings
from src.logger import get_logger

logger = get_logger(__name__)


class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.
    
    This interface defines the contract for all embedding implementations.
    Following the Interface Segregation Principle, it only includes
    methods essential for embedding generation.
    
    Attributes:
        dimension: The dimensionality of output vectors
        
    Methods:
        embed: Embed a single text
        embed_batch: Embed multiple texts efficiently
    """
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimensionality of embedding vectors."""
        pass
    
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        pass
    
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embedding vectors
        """
        pass


class EmbeddingCache:
    """
    Simple file-based cache for embeddings to reduce API costs.
    
    Stores embeddings by content hash so identical texts
    don't require repeated API calls.
    """
    
    def __init__(self, cache_dir: str = ".embedding_cache"):
        """
        Initialize the embedding cache.
        
        Args:
            cache_dir: Directory to store cached embeddings
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: Dict[str, List[float]] = {}
    
    @staticmethod
    def _hash_text(text: str) -> str:
        """Generate a hash for the text content."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    
    def get(self, text: str) -> Optional[List[float]]:
        """
        Retrieve cached embedding if available.
        
        Args:
            text: The original text
            
        Returns:
            Cached embedding vector or None
        """
        text_hash = self._hash_text(text)
        
        # Check memory cache first
        if text_hash in self._memory_cache:
            return self._memory_cache[text_hash]
        
        # Check file cache
        cache_file = self.cache_dir / f"{text_hash}.json"
        if cache_file.exists():
            try:
                embedding = json.loads(cache_file.read_text())
                self._memory_cache[text_hash] = embedding
                return embedding
            except (json.JSONDecodeError, IOError):
                return None
        
        return None
    
    def set(self, text: str, embedding: List[float]) -> None:
        """
        Store embedding in cache.
        
        Args:
            text: The original text
            embedding: The embedding vector to cache
        """
        text_hash = self._hash_text(text)
        
        # Store in memory
        self._memory_cache[text_hash] = embedding
        
        # Store in file
        cache_file = self.cache_dir / f"{text_hash}.json"
        try:
            cache_file.write_text(json.dumps(embedding))
        except IOError as e:
            logger.warning(f"Failed to write embedding cache: {e}")


class AzureEmbeddingProvider(EmbeddingProvider):
    """
    Azure OpenAI embedding provider implementation.
    
    Uses Azure's text-embedding-3-large model to generate
    high-quality 3072-dimensional embeddings.
    
    Features:
    - Automatic batching with configurable batch size
    - Retry logic with exponential backoff
    - Optional caching to reduce API costs
    - Vector normalization for cosine similarity
    
    Example:
        provider = AzureEmbeddingProvider()
        
        # Single embedding
        vector = provider.embed("Hello world")
        
        # Batch embedding
        vectors = provider.embed_batch(["Hello", "World"])
    """
    
    # text-embedding-3-large produces 3072-dimensional vectors
    EMBEDDING_DIMENSION = 3072
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        deployment: Optional[str] = None,
        api_version: Optional[str] = None,
        batch_size: Optional[int] = None,
        max_retries: Optional[int] = None,
        normalize: bool = True,
        use_cache: Optional[bool] = None
    ):
        """
        Initialize the Azure embedding provider.
        
        Args:
            api_key: Azure OpenAI API key (defaults to settings)
            endpoint: Azure OpenAI endpoint URL (defaults to settings)
            deployment: Deployment name (defaults to settings)
            api_version: API version (defaults to settings)
            batch_size: Number of texts to embed per API call (defaults to settings)
            max_retries: Maximum retry attempts on failure (defaults to settings)
            normalize: Whether to normalize vectors for cosine similarity
            use_cache: Whether to cache embeddings (defaults to settings)
        """
        self.api_key = api_key or settings.azure.api_key
        self.endpoint = endpoint or settings.azure.endpoint
        self.deployment = deployment or settings.azure.embedding_deployment
        self.api_version = api_version or settings.azure.api_version
        self.batch_size = batch_size or settings.embedding.batch_size
        self.max_retries = max_retries or settings.embedding.max_retries
        self.normalize = normalize
        
        # Initialize cache if enabled
        use_cache = use_cache if use_cache is not None else settings.embedding.enable_cache
        self._cache = EmbeddingCache() if use_cache else None
        
        logger.info(
            f"Initialized AzureEmbeddingProvider: deployment={self.deployment}, "
            f"batch_size={self.batch_size}, max_retries={self.max_retries}, "
            f"cache={'enabled' if self._cache else 'disabled'}"
        )
    
    @property
    def dimension(self) -> int:
        """Return embedding dimension (3072 for text-embedding-3-large)."""
        return self.EMBEDDING_DIMENSION
    
    @property
    def _url(self) -> str:
        """Construct the Azure OpenAI embedding API URL."""
        base = self.endpoint.rstrip("/")
        return f"{base}/openai/deployments/{self.deployment}/embeddings?api-version={self.api_version}"
    
    @property
    def _headers(self) -> Dict[str, str]:
        """Return HTTP headers for API requests."""
        return {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    @staticmethod
    def _normalize_vector(vector: List[float]) -> List[float]:
        """
        Normalize a vector to unit length for cosine similarity.
        
        Args:
            vector: Input vector
            
        Returns:
            Normalized vector with L2 norm = 1
        """
        norm = math.sqrt(sum(x * x for x in vector))
        if norm == 0:
            return vector
        return [x / norm for x in vector]
    
    def _call_api(self, texts: List[str]) -> List[List[float]]:
        """
        Make API call to Azure OpenAI with retry logic.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            requests.RequestException: If all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self._url,
                    headers=self._headers,
                    json={"input": texts},
                    timeout=60
                )
                
                # Handle rate limiting (429) - unlikely with 60K TPM
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 2))
                    logger.warning(f"Rate limited (429), waiting {retry_after}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(retry_after)
                    continue
                
                # Handle server errors (5xx)
                if response.status_code >= 500:
                    wait_time = 2 ** attempt
                    logger.warning(f"Server error ({response.status_code}), retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                
                # Extract embeddings from response
                data = response.json()
                embeddings = [item["embedding"] for item in data["data"]]
                
                # Normalize if requested
                if self.normalize:
                    embeddings = [self._normalize_vector(e) for e in embeddings]
                
                return embeddings
                
            except requests.RequestException as e:
                last_exception = e
                wait_time = 2 ** attempt
                logger.warning(f"API call failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(wait_time)
        
        raise last_exception or RuntimeError("Failed to get embeddings")
    
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector (3072 dimensions)
        """
        # Check cache first
        if self._cache:
            cached = self._cache.get(text)
            if cached:
                logger.debug("Cache hit for embedding")
                return cached
        
        # Call API
        embeddings = self._call_api([text])
        embedding = embeddings[0]
        
        # Cache result
        if self._cache:
            self._cache.set(text, embedding)
        
        return embedding
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Handles caching, batching, and API calls automatically.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors in same order as input
        """
        if not texts:
            return []
        
        results: List[Optional[List[float]]] = [None] * len(texts)
        texts_to_embed: List[tuple[int, str]] = []  # (original_index, text)
        
        # Check cache for each text
        for i, text in enumerate(texts):
            if self._cache:
                cached = self._cache.get(text)
                if cached:
                    results[i] = cached
                    continue
            texts_to_embed.append((i, text))
        
        if texts_to_embed:
            logger.info(f"Embedding {len(texts_to_embed)} texts ({len(texts) - len(texts_to_embed)} cached)")
            
            # Process in batches
            total_batches = (len(texts_to_embed) + self.batch_size - 1) // self.batch_size
            delay = settings.embedding.delay_between_calls
            
            for batch_idx, batch_start in enumerate(range(0, len(texts_to_embed), self.batch_size)):
                batch = texts_to_embed[batch_start:batch_start + self.batch_size]
                batch_texts = [text for _, text in batch]
                
                if total_batches > 1:
                    logger.debug(f"Processing batch {batch_idx + 1}/{total_batches} ({len(batch_texts)} texts)")
                
                embeddings = self._call_api(batch_texts)
                
                # Store results and cache
                for (original_idx, text), embedding in zip(batch, embeddings):
                    results[original_idx] = embedding
                    if self._cache:
                        self._cache.set(text, embedding)
                
                # Small delay between batches (only if multiple batches)
                if batch_idx < total_batches - 1 and delay > 0:
                    time.sleep(delay)
        
        return results  # type: ignore
