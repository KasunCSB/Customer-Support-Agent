"""
Vector Store Module

This module provides abstractions and implementations for vector storage and search.
It stores document embeddings and enables fast similarity-based retrieval.

Architecture:
- VectorStore: Abstract base class defining the interface (ISP)
- ChromaVectorStore: Concrete implementation using ChromaDB
- Support for metadata storage and filtering

SOLID Principles:
- Interface Segregation: Focused VectorStore interface
- Dependency Inversion: Code depends on VectorStore abstraction
- Single Responsibility: Only handles vector storage/retrieval
- Open/Closed: New stores (Qdrant, Pinecone) can be added

Usage:
    from src.core.vectorstore import ChromaVectorStore
    
    store = ChromaVectorStore()
    store.add_documents(docs, embeddings, metadatas, ids)
    results = store.search(query_embedding, top_k=5)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Sequence, cast

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.config import settings
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """
    Container for a single search result.
    
    Attributes:
        id: Unique identifier of the document
        text: The document text content
        metadata: Additional metadata (source, chunk_index, etc.)
        distance: Similarity distance (lower = more similar for cosine)
        score: Similarity score (higher = more similar)
    """
    id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    distance: float = 0.0
    score: float = 0.0
    
    def __post_init__(self):
        """Calculate score from distance if not provided."""
        if self.score == 0.0 and self.distance > 0:
            # Convert distance to similarity score (1 - distance for cosine)
            self.score = max(0.0, 1.0 - self.distance)


@dataclass
class SearchResults:
    """
    Container for multiple search results.
    
    Attributes:
        results: List of individual SearchResult objects
        query_embedding: The query embedding used (optional)
    """
    results: List[SearchResult] = field(default_factory=list)
    query_embedding: Optional[List[float]] = None
    
    def __iter__(self):
        return iter(self.results)
    
    def __len__(self):
        return len(self.results)
    
    def __getitem__(self, index):
        return self.results[index]
    
    @property
    def texts(self) -> List[str]:
        """Get all result texts."""
        return [r.text for r in self.results]
    
    @property
    def ids(self) -> List[str]:
        """Get all result IDs."""
        return [r.id for r in self.results]
    
    @property
    def metadatas(self) -> List[Dict[str, Any]]:
        """Get all result metadata."""
        return [r.metadata for r in self.results]


class VectorStore(ABC):
    """
    Abstract base class for vector stores.
    
    This interface defines the contract for all vector store implementations.
    It provides methods for adding, searching, and managing document embeddings.
    
    All implementations must support:
    - Adding documents with embeddings and metadata
    - Similarity search by query embedding
    - Document deletion by ID
    - Collection statistics
    """
    
    @abstractmethod
    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents with their embeddings to the store.
        
        Args:
            texts: Document texts
            embeddings: Corresponding embedding vectors
            metadatas: Optional metadata for each document
            ids: Optional unique IDs (generated if not provided)
            
        Returns:
            List of document IDs
        """
        pass
    
    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> SearchResults:
        """
        Search for similar documents by embedding.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            SearchResults containing matching documents
        """
        pass
    
    @abstractmethod
    def delete(self, ids: List[str]) -> None:
        """
        Delete documents by ID.
        
        Args:
            ids: Document IDs to delete
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """
        Get the number of documents in the store.
        
        Returns:
            Document count
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Remove all documents from the store."""
        pass


class ChromaVectorStore(VectorStore):
    """
    ChromaDB implementation of VectorStore.
    
    ChromaDB is a lightweight, embedded vector database that stores
    data locally. Perfect for development and small-to-medium deployments.
    
    Features:
    - Persistent storage with DuckDB backend
    - Metadata filtering support
    - Automatic ID generation
    - HNSW index for fast similarity search
    
    Example:
        store = ChromaVectorStore()
        
        # Add documents
        ids = store.add_documents(
            texts=["Hello world", "Goodbye"],
            embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
            metadatas=[{"source": "doc1"}, {"source": "doc2"}]
        )
        
        # Search
        results = store.search(query_embedding, top_k=5)
        for result in results:
            print(f"{result.text} (score: {result.score})")
    """
    
    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None
    ):
        """
        Initialize ChromaDB vector store.
        
        Args:
            persist_directory: Directory for persistent storage
            collection_name: Name of the collection
        """
        self.persist_directory = persist_directory or settings.vectorstore.directory
        self.collection_name = collection_name or settings.vectorstore.collection
        
        # Ensure directory exists
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize Chroma client with persistence
        self._client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # Get or create collection.
        # Keep metadata minimal for compatibility across Chroma versions.
        # (Setting advanced HNSW params via metadata has caused startup failures in some environments.)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        
        logger.info(
            f"Initialized ChromaVectorStore: collection={self.collection_name}, "
            f"persist_directory={self.persist_directory}, "
            f"existing_docs={self.count()}"
        )
    
    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents with embeddings to ChromaDB.
        
        Args:
            texts: Document texts
            embeddings: Embedding vectors
            metadatas: Optional metadata dicts
            ids: Optional document IDs
            
        Returns:
            List of assigned document IDs
        """
        if not texts:
            return []
        
        # Generate IDs if not provided
        if ids is None:
            import hashlib
            ids = [
                hashlib.sha256(text.encode()).hexdigest()[:16]
                for text in texts
            ]
        
        # Ensure metadatas list exists
        if metadatas is None:
            metadatas = [{} for _ in texts]
        
        # Add to collection (Chroma handles duplicates by ID)
        # Cast types for ChromaDB compatibility
        self._collection.upsert(
            documents=texts,
            embeddings=cast(Any, embeddings),
            metadatas=cast(Any, metadatas),
            ids=ids
        )
        
        logger.info(f"Added {len(texts)} documents to vector store")
        return ids
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> SearchResults:
        """
        Search for similar documents using cosine similarity.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results
            filter_metadata: Optional metadata filter (e.g., {"source": "faq.pdf"})
            
        Returns:
            SearchResults with matching documents
        """
        # Build query kwargs
        query_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, self.count()) if self.count() > 0 else top_k,
            "include": ["documents", "metadatas", "distances"]
        }
        
        # Add metadata filter if provided
        if filter_metadata:
            query_kwargs["where"] = filter_metadata
        
        # Execute query
        results = self._collection.query(**query_kwargs)
        
        # Parse results into SearchResults
        search_results = []
        
        if results and results.get("ids") and results["ids"][0]:
            ids = results["ids"][0]
            # Safely extract results with defaults
            documents_list = results.get("documents") or [[]]
            metadatas_list = results.get("metadatas") or [[]]
            distances_list = results.get("distances") or [[]]
            
            documents = documents_list[0] if documents_list else []
            metadatas = metadatas_list[0] if metadatas_list else []
            distances = distances_list[0] if distances_list else []
            
            for i, doc_id in enumerate(ids):
                search_results.append(SearchResult(
                    id=doc_id,
                    text=documents[i] if i < len(documents) else "",
                    metadata=dict(metadatas[i]) if i < len(metadatas) else {},
                    distance=distances[i] if i < len(distances) else 0.0
                ))
        
        logger.debug(f"Search returned {len(search_results)} results")
        return SearchResults(results=search_results, query_embedding=query_embedding)
    
    def delete(self, ids: List[str]) -> None:
        """
        Delete documents by ID.
        
        Args:
            ids: Document IDs to delete
        """
        if ids:
            self._collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents from vector store")
    
    def count(self) -> int:
        """Get number of documents in collection."""
        return self._collection.count()
    
    def clear(self) -> None:
        """Remove all documents from the collection."""
        # Chroma doesn't have a direct clear method, so recreate collection
        self._client.delete_collection(name=self.collection_name)
        self._collection = self._client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("Cleared all documents from vector store")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary with store statistics
        """
        return {
            "collection_name": self.collection_name,
            "document_count": self.count(),
            "persist_directory": self.persist_directory
        }
