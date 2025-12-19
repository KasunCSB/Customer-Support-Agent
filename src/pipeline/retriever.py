"""
Retriever Module

This module provides the retrieval component of the RAG pipeline.
It combines embedding and vector store to find relevant documents.

Architecture:
- Retriever: Main class orchestrating embedding + search
- RetrievalResult: Container for retrieval results with context

SOLID Principles:
- Single Responsibility: Only handles retrieval logic
- Dependency Inversion: Depends on abstractions (EmbeddingProvider, VectorStore)
- Open/Closed: Can use any embedding/vectorstore implementation

Usage:
    from src.pipeline.retriever import Retriever
    
    retriever = Retriever(embedding_provider, vector_store)
    results = retriever.retrieve("How do I reset my password?", top_k=5)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from src.core.embeddings import EmbeddingProvider
from src.core.vectorstore import VectorStore, SearchResults, SearchResult
from src.config import settings
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    """
    Container for retrieval results.
    
    Provides convenient access to retrieved documents and
    formatted context for LLM consumption.
    
    Attributes:
        query: Original query text
        results: List of search results
        query_embedding: Embedding of the query
    """
    query: str
    results: List[SearchResult] = field(default_factory=list)
    query_embedding: Optional[List[float]] = None
    
    def __iter__(self):
        return iter(self.results)
    
    def __len__(self):
        return len(self.results)
    
    @property
    def texts(self) -> List[str]:
        """Get all result texts."""
        return [r.text for r in self.results]
    
    @property
    def has_results(self) -> bool:
        """Check if any results were found."""
        return len(self.results) > 0
    
    def format_context(
        self,
        include_source: bool = True,
        max_tokens: Optional[int] = None,
        separator: str = "\n\n---\n\n"
    ) -> str:
        """
        Format retrieved documents as context string for LLM.
        
        Args:
            include_source: Include source metadata in context
            max_tokens: Maximum tokens to include (approximate)
            separator: String to separate documents
            
        Returns:
            Formatted context string
        """
        if not self.results:
            return ""
        
        context_parts = []
        
        for i, result in enumerate(self.results, 1):
            if include_source:
                source = result.metadata.get("source", "Unknown")
                chunk_idx = result.metadata.get("chunk_index", 0)
                header = f"[Source: {source}, Chunk: {chunk_idx}]"
                context_parts.append(f"{header}\n{result.text}")
            else:
                context_parts.append(result.text)
        
        full_context = separator.join(context_parts)
        
        # TODO: Implement proper token-based truncation
        # For now, use character-based approximation (4 chars ≈ 1 token)
        if max_tokens:
            max_chars = max_tokens * 4
            if len(full_context) > max_chars:
                full_context = full_context[:max_chars] + "..."
        
        return full_context
    
    def get_sources(self) -> List[Dict[str, Any]]:
        """
        Get unique sources from results.
        
        Returns:
            List of source metadata dicts
        """
        seen = set()
        sources = []
        
        for result in self.results:
            source = result.metadata.get("source", "Unknown")
            if source not in seen:
                seen.add(source)
                sources.append({
                    "source": source,
                    "metadata": result.metadata
                })
        
        return sources


class Retriever:
    """
    Document retriever combining embeddings and vector search.
    
    This class orchestrates the retrieval process:
    1. Embed the query using the embedding provider
    2. Search the vector store for similar documents
    3. Format results for downstream processing
    
    Example:
        from src.core.embeddings import AzureEmbeddingProvider
        from src.core.vectorstore import ChromaVectorStore
        
        retriever = Retriever(
            embedding_provider=AzureEmbeddingProvider(),
            vector_store=ChromaVectorStore()
        )
        
        results = retriever.retrieve("How do I reset my password?")
        print(results.format_context())
    """
    
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        default_top_k: Optional[int] = None
    ):
        """
        Initialize the retriever.
        
        Args:
            embedding_provider: Provider for query embeddings
            vector_store: Store for document search
            default_top_k: Default number of results to return
        """
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.default_top_k = default_top_k or settings.retrieval.top_k
        
        logger.info(f"Initialized Retriever with top_k={self.default_top_k}")
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> RetrievalResult:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: Query text
            top_k: Number of results to return
            filter_metadata: Optional metadata filter
            
        Returns:
            RetrievalResult with matching documents
        """
        top_k = top_k or self.default_top_k
        
        logger.debug(f"Retrieving top {top_k} results for query: {query[:50]}...")
        
        # Embed the query
        query_embedding = self.embedding_provider.embed(query)
        
        # Search vector store
        search_results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_metadata=filter_metadata
        )
        
        logger.info(f"Retrieved {len(search_results)} results for query")
        
        return RetrievalResult(
            query=query,
            results=search_results.results,
            query_embedding=query_embedding
        )
    
    def retrieve_with_threshold(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: float = 0.5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> RetrievalResult:
        """
        Retrieve documents with minimum similarity threshold.
        
        Only returns documents with similarity score >= threshold.
        
        Args:
            query: Query text
            top_k: Maximum results to return
            score_threshold: Minimum similarity score (0-1)
            filter_metadata: Optional metadata filter
            
        Returns:
            RetrievalResult with filtered matching documents
        """
        result = self.retrieve(
            query=query,
            top_k=top_k,
            filter_metadata=filter_metadata
        )
        
        # Filter by score threshold
        filtered_results = [
            r for r in result.results
            if r.score >= score_threshold
        ]
        
        logger.debug(
            f"Filtered {len(result.results)} results to {len(filtered_results)} "
            f"with threshold {score_threshold}"
        )
        
        return RetrievalResult(
            query=result.query,
            results=filtered_results,
            query_embedding=result.query_embedding
        )
    
    @property
    def document_count(self) -> int:
        """Get number of documents in the vector store."""
        return self.vector_store.count()
