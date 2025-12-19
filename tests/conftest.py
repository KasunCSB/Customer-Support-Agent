"""
Pytest Configuration and Fixtures

This module provides shared fixtures and configuration for all tests.
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment
os.environ["APP_ENV"] = "test"
os.environ["AZURE_OPENAI_API_KEY"] = "test-key"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test.openai.azure.com"
os.environ["VECTORSTORE_DIR"] = "/tmp/test_vectorstore"


@pytest.fixture
def sample_texts():
    """Sample texts for testing."""
    return [
        "How do I reset my password? Click 'Forgot Password' on the login page.",
        "What payment methods do you accept? We accept Visa, MasterCard, and PayPal.",
        "How can I track my order? Log into your account and go to Order History.",
    ]


@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    return [
        {
            "text": "To reset your password, click on 'Forgot Password' at the login page. Enter your email and follow the link sent to you.",
            "source": "faq.pdf",
            "category": "account"
        },
        {
            "text": "We accept the following payment methods: Visa, MasterCard, American Express, PayPal, and Apple Pay.",
            "source": "billing.md",
            "category": "billing"
        },
        {
            "text": "To track your order, log into your account, go to 'Order History', and click 'Track Order' next to your purchase.",
            "source": "orders.txt",
            "category": "orders"
        }
    ]


@pytest.fixture
def mock_embedding():
    """Mock embedding vector (3072 dimensions)."""
    import random
    random.seed(42)
    return [random.random() for _ in range(3072)]


@pytest.fixture
def mock_embeddings(mock_embedding):
    """Multiple mock embeddings."""
    import random
    embeddings = []
    for i in range(5):
        random.seed(42 + i)
        embeddings.append([random.random() for _ in range(3072)])
    return embeddings


@pytest.fixture
def mock_embedding_provider(mock_embedding):
    """Mock embedding provider."""
    provider = MagicMock()
    provider.dimension = 3072
    provider.embed.return_value = mock_embedding
    provider.embed_batch.return_value = [mock_embedding] * 3
    return provider


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider."""
    from src.core.llm import ChatResponse
    
    provider = MagicMock()
    provider.chat.return_value = ChatResponse(
        content="This is a test response.",
        model="gpt-4o-mini",
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    )
    return provider


@pytest.fixture
def temp_vectorstore_dir(tmp_path):
    """Temporary directory for vector store."""
    store_dir = tmp_path / "vectorstore"
    store_dir.mkdir()
    return str(store_dir)


@pytest.fixture
def mock_chroma_client():
    """Mock ChromaDB client."""
    with patch("chromadb.PersistentClient") as mock:
        collection = MagicMock()
        collection.count.return_value = 0
        mock.return_value.get_or_create_collection.return_value = collection
        yield mock


@pytest.fixture
def sample_jsonl_file(tmp_path):
    """Create a sample JSONL file for testing."""
    import json
    
    data = [
        {"id": "1", "question": "How to reset password?", "answer": "Click forgot password."},
        {"id": "2", "question": "Payment methods?", "answer": "Visa, MasterCard, PayPal."},
    ]
    
    filepath = tmp_path / "test_data.jsonl"
    with open(filepath, "w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
    
    return filepath
