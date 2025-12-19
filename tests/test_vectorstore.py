"""
Tests for Vector Store Module

Tests ChromaVectorStore and related classes.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestSearchResult:
    """Tests for SearchResult dataclass."""
    
    def test_search_result_creation(self):
        """Test basic SearchResult creation."""
        from src.core.vectorstore import SearchResult
        
        result = SearchResult(
            id="doc1",
            text="Hello world",
            metadata={"source": "test.txt"},
            distance=0.1
        )
        
        assert result.id == "doc1"
        assert result.text == "Hello world"
        assert result.distance == 0.1
        assert result.score == pytest.approx(0.9, abs=0.01)
    
    def test_search_result_score_calculation(self):
        """Test score is calculated from distance."""
        from src.core.vectorstore import SearchResult
        
        result = SearchResult(id="1", text="test", distance=0.3)
        assert result.score == pytest.approx(0.7, abs=0.01)


class TestSearchResults:
    """Tests for SearchResults container."""
    
    def test_search_results_iteration(self):
        """Test SearchResults is iterable."""
        from src.core.vectorstore import SearchResult, SearchResults
        
        results = SearchResults(results=[
            SearchResult(id="1", text="a"),
            SearchResult(id="2", text="b"),
        ])
        
        texts = [r.text for r in results]
        assert texts == ["a", "b"]
    
    def test_search_results_length(self):
        """Test SearchResults length."""
        from src.core.vectorstore import SearchResult, SearchResults
        
        results = SearchResults(results=[
            SearchResult(id="1", text="a"),
            SearchResult(id="2", text="b"),
        ])
        
        assert len(results) == 2
    
    def test_search_results_indexing(self):
        """Test SearchResults indexing."""
        from src.core.vectorstore import SearchResult, SearchResults
        
        results = SearchResults(results=[
            SearchResult(id="1", text="a"),
            SearchResult(id="2", text="b"),
        ])
        
        assert results[0].text == "a"
        assert results[1].text == "b"
    
    def test_search_results_properties(self):
        """Test SearchResults helper properties."""
        from src.core.vectorstore import SearchResult, SearchResults
        
        results = SearchResults(results=[
            SearchResult(id="1", text="a", metadata={"source": "x"}),
            SearchResult(id="2", text="b", metadata={"source": "y"}),
        ])
        
        assert results.texts == ["a", "b"]
        assert results.ids == ["1", "2"]
        assert len(results.metadatas) == 2


class TestChromaVectorStore:
    """Tests for ChromaVectorStore."""
    
    @pytest.fixture
    def mock_chroma(self):
        """Create mock ChromaDB client and collection."""
        with patch("src.core.vectorstore.chromadb") as mock_chromadb:
            mock_collection = MagicMock()
            mock_collection.count.return_value = 0
            mock_collection.query.return_value = {
                "ids": [["1", "2"]],
                "documents": [["doc1", "doc2"]],
                "metadatas": [[{"source": "a"}, {"source": "b"}]],
                "distances": [[0.1, 0.2]]
            }
            
            mock_client = MagicMock()
            mock_client.get_or_create_collection.return_value = mock_collection
            mock_chromadb.PersistentClient.return_value = mock_client
            
            yield {
                "chromadb": mock_chromadb,
                "client": mock_client,
                "collection": mock_collection
            }
    
    def test_store_initialization(self, mock_chroma, temp_vectorstore_dir):
        """Test vector store initializes correctly."""
        from src.core.vectorstore import ChromaVectorStore
        
        store = ChromaVectorStore(
            persist_directory=temp_vectorstore_dir,
            collection_name="test_collection"
        )
        
        mock_chroma["client"].get_or_create_collection.assert_called_once()
    
    def test_add_documents(self, mock_chroma, temp_vectorstore_dir, mock_embeddings):
        """Test adding documents to store."""
        from src.core.vectorstore import ChromaVectorStore
        
        store = ChromaVectorStore(
            persist_directory=temp_vectorstore_dir,
            collection_name="test_collection"
        )
        
        texts = ["doc1", "doc2", "doc3"]
        embeddings = mock_embeddings[:3]
        metadatas = [{"source": "a"}, {"source": "b"}, {"source": "c"}]
        
        ids = store.add_documents(texts, embeddings, metadatas)
        
        assert len(ids) == 3
        mock_chroma["collection"].upsert.assert_called_once()
    
    def test_search(self, mock_chroma, temp_vectorstore_dir, mock_embedding):
        """Test searching documents."""
        from src.core.vectorstore import ChromaVectorStore
        
        # Set count to non-zero so search proceeds
        mock_chroma["collection"].count.return_value = 10
        
        store = ChromaVectorStore(
            persist_directory=temp_vectorstore_dir,
            collection_name="test_collection"
        )
        
        results = store.search(mock_embedding, top_k=5)
        
        assert len(results) == 2  # Based on mock response
        assert results[0].text == "doc1"
        assert results[0].distance == 0.1
    
    def test_search_empty_store(self, mock_chroma, temp_vectorstore_dir, mock_embedding):
        """Test searching empty store."""
        from src.core.vectorstore import ChromaVectorStore
        
        mock_chroma["collection"].count.return_value = 0
        mock_chroma["collection"].query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }
        
        store = ChromaVectorStore(
            persist_directory=temp_vectorstore_dir,
            collection_name="test_collection"
        )
        
        results = store.search(mock_embedding, top_k=5)
        
        assert len(results) == 0
    
    def test_delete(self, mock_chroma, temp_vectorstore_dir):
        """Test deleting documents."""
        from src.core.vectorstore import ChromaVectorStore
        
        store = ChromaVectorStore(
            persist_directory=temp_vectorstore_dir,
            collection_name="test_collection"
        )
        
        store.delete(["id1", "id2"])
        
        mock_chroma["collection"].delete.assert_called_once_with(ids=["id1", "id2"])
    
    def test_count(self, mock_chroma, temp_vectorstore_dir):
        """Test document count."""
        from src.core.vectorstore import ChromaVectorStore
        
        mock_chroma["collection"].count.return_value = 42
        
        store = ChromaVectorStore(
            persist_directory=temp_vectorstore_dir,
            collection_name="test_collection"
        )
        
        assert store.count() == 42
    
    def test_get_stats(self, mock_chroma, temp_vectorstore_dir):
        """Test getting store statistics."""
        from src.core.vectorstore import ChromaVectorStore
        
        mock_chroma["collection"].count.return_value = 100
        
        store = ChromaVectorStore(
            persist_directory=temp_vectorstore_dir,
            collection_name="test_collection"
        )
        
        stats = store.get_stats()
        
        assert stats["collection_name"] == "test_collection"
        assert stats["document_count"] == 100
