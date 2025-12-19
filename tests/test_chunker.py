"""
Tests for Text Chunker Module

Tests the TextChunker class and its chunking strategies.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestChunk:
    """Tests for the Chunk dataclass."""
    
    def test_chunk_creation(self):
        """Test basic chunk creation."""
        from src.pipeline.chunker import Chunk
        
        chunk = Chunk(
            text="Hello world",
            index=0,
            start_token=0,
            end_token=2,
            metadata={"source": "test.txt"}
        )
        
        assert chunk.text == "Hello world"
        assert chunk.index == 0
        assert chunk.metadata["source"] == "test.txt"
    
    def test_chunk_id_generation(self):
        """Test chunk ID generation."""
        from src.pipeline.chunker import Chunk
        
        chunk1 = Chunk(text="Hello", index=0, metadata={"source": "a.txt"})
        chunk2 = Chunk(text="Hello", index=0, metadata={"source": "a.txt"})
        chunk3 = Chunk(text="World", index=0, metadata={"source": "a.txt"})
        
        # Same content should generate same ID
        assert chunk1.id == chunk2.id
        # Different content should generate different ID
        assert chunk1.id != chunk3.id


class TestTextChunker:
    """Tests for the TextChunker class."""
    
    @pytest.fixture
    def chunker(self):
        """Create a chunker with test settings."""
        from src.pipeline.chunker import TextChunker
        return TextChunker(chunk_size=100, overlap=20)
    
    def test_count_tokens(self, chunker):
        """Test token counting."""
        text = "Hello, world! This is a test."
        count = chunker.count_tokens(text)
        
        assert isinstance(count, int)
        assert count > 0
        assert count < len(text)  # Tokens should be fewer than characters
    
    def test_chunk_short_text(self, chunker):
        """Test chunking text shorter than chunk_size."""
        text = "This is a short text."
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].index == 0
    
    def test_chunk_long_text(self, chunker):
        """Test chunking text longer than chunk_size."""
        # Create text that will require multiple chunks
        text = "This is a test sentence. " * 50
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 1
        # Check indices are sequential
        for i, chunk in enumerate(chunks):
            assert chunk.index == i
    
    def test_chunk_with_metadata(self, chunker):
        """Test that metadata is preserved in chunks."""
        text = "Test text " * 20
        metadata = {"source": "test.pdf", "page": 1}
        
        chunks = chunker.chunk_text(text, metadata=metadata)
        
        for chunk in chunks:
            assert chunk.metadata["source"] == "test.pdf"
            assert chunk.metadata["page"] == 1
            assert "chunk_index" in chunk.metadata
    
    def test_chunk_empty_text(self, chunker):
        """Test chunking empty text."""
        chunks = chunker.chunk_text("")
        assert len(chunks) == 0
        
        chunks = chunker.chunk_text("   ")
        assert len(chunks) == 0
    
    def test_chunk_overlap(self, chunker):
        """Test that chunks have proper overlap."""
        # Create text that will have multiple chunks
        text = "Word " * 200
        chunks = chunker.chunk_text(text)
        
        if len(chunks) > 1:
            # Each chunk after the first should start before the previous ends
            for i in range(1, len(chunks)):
                # With overlap, start of chunk[i] should be < end of chunk[i-1]
                assert chunks[i].start_token < chunks[i-1].end_token
    
    def test_chunk_documents(self, chunker, sample_documents):
        """Test chunking multiple documents."""
        chunks = chunker.chunk_documents(sample_documents)
        
        assert len(chunks) > 0
        # Each chunk should have document metadata
        for chunk in chunks:
            assert "document_index" in chunk.metadata


class TestChunkTextSimple:
    """Tests for the simple chunking utility function."""
    
    def test_simple_chunking(self):
        """Test the simple chunking function."""
        from src.pipeline.chunker import chunk_text_simple
        
        text = "Hello world. " * 100
        chunks = chunk_text_simple(text, chunk_size=50, overlap=10)
        
        assert isinstance(chunks, list)
        assert all(isinstance(c, str) for c in chunks)
        assert len(chunks) > 1
