"""
Text Chunking Module

This module provides intelligent text chunking for document processing.
It splits documents into semantically meaningful chunks while respecting
token limits and maintaining context through overlap.

Features:
- Token-aware chunking using tiktoken
- Configurable chunk size and overlap
- Metadata preservation
- Multiple chunking strategies

SOLID Principles:
- Single Responsibility: Only handles text chunking
- Open/Closed: Chunking strategies can be extended
- Dependency Inversion: Uses tokenizer abstraction

Usage:
    from src.pipeline.chunker import TextChunker
    
    chunker = TextChunker(chunk_size=1000, overlap=200)
    chunks = chunker.chunk_text(document_text, metadata={"source": "doc.pdf"})
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
import re

import tiktoken

from src.config import settings
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Chunk:
    """
    Represents a single chunk of text with metadata.
    
    Attributes:
        text: The chunk text content
        index: Position of this chunk in the document
        start_token: Starting token position in original document
        end_token: Ending token position in original document
        token_count: Number of tokens in this chunk
        metadata: Additional metadata (source, etc.)
    """
    text: str
    index: int = 0
    start_token: int = 0
    end_token: int = 0
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate token count if not provided."""
        if self.token_count == 0 and self.text:
            self.token_count = self.end_token - self.start_token
    
    @property
    def id(self) -> str:
        """Generate a unique ID for this chunk based on content and position."""
        import hashlib
        # Include a document-level identity when available.
        # Without this, chunks from different JSONL rows in the same source file can collide
        # (same chunk index + same prefix text), causing Chroma upsert duplicate-id errors.
        doc_identity = (
            self.metadata.get("doc_id")
            or self.metadata.get("document_id")
            or self.metadata.get("id")
            or self.metadata.get("document_index")
            or self.metadata.get("index")
            or ""
        )
        content = f"{self.metadata.get('source', '')}:{doc_identity}:{self.index}:{self.text[:50]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class TextChunker:
    """
    Token-aware text chunker with configurable strategies.
    
    Splits text into chunks while:
    - Respecting token limits for embedding models
    - Maintaining semantic coherence via overlap
    - Preserving document structure when possible
    - Tracking metadata through chunking
    
    Example:
        chunker = TextChunker(chunk_size=1000, overlap=200)
        
        # Simple chunking
        chunks = chunker.chunk_text("Long document text...")
        
        # With metadata
        chunks = chunker.chunk_text(
            text="Document content...",
            metadata={"source": "manual.pdf", "page": 5}
        )
    """
    
    # Supported models for tokenization
    SUPPORTED_MODELS = {
        "gpt-4o-mini": "o200k_base",
        "gpt-4o": "o200k_base",
        "gpt-4": "cl100k_base",
        "gpt-3.5-turbo": "cl100k_base",
        "text-embedding-3-large": "cl100k_base",
        "text-embedding-3-small": "cl100k_base",
    }
    
    def __init__(
        self,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
        model: str = "gpt-4o-mini",
        respect_sentences: bool = True
    ):
        """
        Initialize the text chunker.
        
        Args:
            chunk_size: Maximum tokens per chunk (defaults to settings)
            overlap: Token overlap between chunks (defaults to settings)
            model: Model name for tokenization
            respect_sentences: Try to break at sentence boundaries
        """
        self.chunk_size = chunk_size or settings.chunking.chunk_size
        self.overlap = overlap or settings.chunking.chunk_overlap
        self.respect_sentences = respect_sentences
        
        # Initialize tokenizer
        encoding_name = self.SUPPORTED_MODELS.get(model, "cl100k_base")
        self._encoder = tiktoken.get_encoding(encoding_name)
        
        logger.info(
            f"Initialized TextChunker: chunk_size={self.chunk_size}, "
            f"overlap={self.overlap}, encoding={encoding_name}"
        )
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string.
        
        Args:
            text: Input text
            
        Returns:
            Number of tokens
        """
        return len(self._encoder.encode(text))
    
    def _find_sentence_boundary(
        self,
        tokens: List[int],
        target_position: int,
        search_range: int = 50
    ) -> int:
        """
        Find the nearest sentence boundary to a target position.
        
        Args:
            tokens: Token list
            target_position: Target position in tokens
            search_range: How far to search for boundary
            
        Returns:
            Adjusted position at sentence boundary
        """
        if not self.respect_sentences:
            return target_position
        
        # Decode tokens around target position
        start = max(0, target_position - search_range)
        end = min(len(tokens), target_position + search_range)
        
        text_segment = self._encoder.decode(tokens[start:end])
        
        # Find sentence boundaries (., !, ?, newlines)
        sentence_pattern = r'[.!?]\s+|\n\n'
        
        # Look for boundaries and find closest to middle of segment
        relative_target = target_position - start
        best_boundary = relative_target
        best_distance = float('inf')
        
        for match in re.finditer(sentence_pattern, text_segment):
            boundary_pos = match.end()
            # Convert character position to approximate token position
            char_ratio = len(text_segment) / (end - start)
            token_pos = int(boundary_pos / char_ratio)
            distance = abs(token_pos - relative_target)
            
            if distance < best_distance and distance < search_range:
                best_distance = distance
                best_boundary = token_pos
        
        return start + best_boundary
    
    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Split text into token-aware chunks with overlap.
        
        Args:
            text: Input text to chunk
            metadata: Metadata to attach to all chunks
            
        Returns:
            List of Chunk objects
        """
        if not text or not text.strip():
            return []
        
        metadata = metadata or {}
        
        # Tokenize full text
        tokens = self._encoder.encode(text)
        total_tokens = len(tokens)
        
        if total_tokens <= self.chunk_size:
            # Text fits in one chunk
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_index"] = 0
            chunk_metadata["token_count"] = total_tokens
            return [Chunk(
                text=text,
                index=0,
                start_token=0,
                end_token=total_tokens,
                token_count=total_tokens,
                metadata=chunk_metadata
            )]
        
        chunks = []
        position = 0
        chunk_index = 0
        
        while position < total_tokens:
            # Calculate end position for this chunk
            end_position = min(position + self.chunk_size, total_tokens)
            
            # Try to find sentence boundary for cleaner breaks
            if end_position < total_tokens:
                end_position = self._find_sentence_boundary(
                    tokens, end_position, search_range=50
                )
            
            # Extract chunk tokens and decode
            chunk_tokens = tokens[position:end_position]
            chunk_text = self._encoder.decode(chunk_tokens)
            
            # Create chunk with metadata
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_index"] = chunk_index
            chunk_metadata["token_count"] = len(chunk_tokens)
            
            chunks.append(Chunk(
                text=chunk_text,
                index=chunk_index,
                start_token=position,
                end_token=end_position,
                token_count=len(chunk_tokens),
                metadata=chunk_metadata
            ))
            
            # Move position with overlap
            position = end_position - self.overlap
            if position <= chunks[-1].start_token:
                # Prevent infinite loop for small texts
                position = end_position
            
            chunk_index += 1
        
        logger.debug(f"Created {len(chunks)} chunks from {total_tokens} tokens")
        return chunks
    
    def chunk_documents(
        self,
        documents: List[Dict[str, Any]],
        text_key: str = "text",
        metadata_keys: Optional[List[str]] = None
    ) -> List[Chunk]:
        """
        Chunk multiple documents with their metadata.
        
        Args:
            documents: List of document dicts with text and metadata
            text_key: Key for text content in document dict
            metadata_keys: Keys to include in chunk metadata
            
        Returns:
            List of all chunks from all documents
        """
        all_chunks = []
        
        for doc_idx, doc in enumerate(documents):
            text = doc.get(text_key, "")
            if not text:
                continue
            
            # Build metadata from document
            metadata = {"document_index": doc_idx}
            if metadata_keys:
                for key in metadata_keys:
                    if key in doc:
                        metadata[key] = doc[key]
            else:
                # Include all keys except text_key
                for key, value in doc.items():
                    if key != text_key:
                        metadata[key] = value
            
            # Chunk this document
            chunks = self.chunk_text(text, metadata=metadata)
            all_chunks.extend(chunks)
        
        logger.info(f"Created {len(all_chunks)} chunks from {len(documents)} documents")
        return all_chunks


def chunk_text_simple(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200
) -> List[str]:
    """
    Simple utility function for quick text chunking.
    
    Args:
        text: Input text
        chunk_size: Max tokens per chunk
        overlap: Token overlap
        
    Returns:
        List of chunk text strings
    """
    chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
    return [c.text for c in chunker.chunk_text(text)]
