"""
Core Module Package

This package contains the core abstractions and implementations for:
- Embeddings: Converting text to vector representations
- Vector Store: Storing and searching vector embeddings
- LLM: Language model interactions for response generation

All modules follow the Interface Segregation Principle (ISP) and
Dependency Inversion Principle (DIP) from SOLID.
"""

from src.core.embeddings import EmbeddingProvider, AzureEmbeddingProvider
from src.core.vectorstore import VectorStore, ChromaVectorStore
from src.core.llm import LLMProvider, AzureLLMProvider

__all__ = [
    "EmbeddingProvider",
    "AzureEmbeddingProvider",
    "VectorStore",
    "ChromaVectorStore",
    "LLMProvider",
    "AzureLLMProvider",
]
