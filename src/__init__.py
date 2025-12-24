"""
Customer Support Agent - Source Package

A RAG-based AI customer support agent using Azure OpenAI and ChromaDB.

This package provides:
- Document ingestion and chunking
- Semantic search via embeddings
- LLM-powered response generation
- CLI interface for interaction

Architecture follows SOLID principles:
- Single Responsibility: Each module handles one concern
- Open/Closed: Interfaces allow extension without modification
- Liskov Substitution: Implementations are interchangeable
- Interface Segregation: Small, focused interfaces
- Dependency Inversion: Depend on abstractions, not concretions
"""

__version__ = "5.0.0"
__author__ = "Kasun Chanaka"
__email__ = "kasuncsb@gmail.com"

from src.config import settings

__all__ = ["settings", "__version__"]
