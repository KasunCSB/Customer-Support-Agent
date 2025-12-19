"""
Tests for Configuration Module

Tests the Settings and configuration management.
"""

import os
import pytest
from unittest.mock import patch


class TestGetEnv:
    """Tests for environment variable helpers."""
    
    def test_get_env_with_default(self):
        """Test getting env var with default."""
        from src.config import get_env
        
        result = get_env("NONEXISTENT_VAR", "default_value")
        assert result == "default_value"
    
    def test_get_env_existing(self):
        """Test getting existing env var."""
        from src.config import get_env
        
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            result = get_env("TEST_VAR")
            assert result == "test_value"
    
    def test_get_env_required_missing(self):
        """Test required env var raises error when missing."""
        from src.config import get_env
        
        with pytest.raises(ValueError):
            get_env("DEFINITELY_NOT_SET", required=True)


class TestGetEnvTyped:
    """Tests for typed environment variable helpers."""
    
    def test_get_env_int(self):
        """Test getting int from env."""
        from src.config import get_env_int
        
        with patch.dict(os.environ, {"INT_VAR": "42"}):
            result = get_env_int("INT_VAR", 0)
            assert result == 42
            assert isinstance(result, int)
    
    def test_get_env_float(self):
        """Test getting float from env."""
        from src.config import get_env_float
        
        with patch.dict(os.environ, {"FLOAT_VAR": "3.14"}):
            result = get_env_float("FLOAT_VAR", 0.0)
            assert result == 3.14
            assert isinstance(result, float)
    
    def test_get_env_bool_true(self):
        """Test getting bool true from env."""
        from src.config import get_env_bool
        
        for true_value in ["true", "True", "TRUE", "1", "yes", "on"]:
            with patch.dict(os.environ, {"BOOL_VAR": true_value}):
                result = get_env_bool("BOOL_VAR", False)
                assert result is True
    
    def test_get_env_bool_false(self):
        """Test getting bool false from env."""
        from src.config import get_env_bool
        
        for false_value in ["false", "False", "0", "no", "off"]:
            with patch.dict(os.environ, {"BOOL_VAR": false_value}):
                result = get_env_bool("BOOL_VAR", True)
                assert result is False


class TestAzureOpenAIConfig:
    """Tests for Azure OpenAI configuration."""
    
    def test_embedding_url(self):
        """Test embedding URL construction."""
        from src.config import AzureOpenAIConfig
        
        config = AzureOpenAIConfig(
            api_key="test",
            endpoint="https://test.openai.azure.com",
            api_version="2024-08-01-preview",
            embedding_deployment="embedding-model"
        )
        
        url = config.embedding_url
        assert "test.openai.azure.com" in url
        assert "embedding-model" in url
        assert "embeddings" in url
        assert "2024-08-01-preview" in url
    
    def test_chat_url(self):
        """Test chat URL construction."""
        from src.config import AzureOpenAIConfig
        
        config = AzureOpenAIConfig(
            api_key="test",
            endpoint="https://test.openai.azure.com/",  # Trailing slash
            api_version="2024-08-01-preview",
            chat_deployment="chat-model"
        )
        
        url = config.chat_url
        assert "chat-model" in url
        assert "chat/completions" in url
        # Should not have double slashes
        assert "//" not in url.replace("https://", "")
    
    def test_validate_missing_key(self):
        """Test validation fails without API key."""
        from src.config import AzureOpenAIConfig
        
        config = AzureOpenAIConfig(
            api_key="",
            endpoint="https://test.openai.azure.com"
        )
        
        with pytest.raises(ValueError, match="API_KEY"):
            config.validate()


class TestChunkingConfig:
    """Tests for chunking configuration."""
    
    def test_validate_invalid_chunk_size(self):
        """Test validation fails with invalid chunk size."""
        from src.config import ChunkingConfig
        
        config = ChunkingConfig()
        config.chunk_size = 0
        
        with pytest.raises(ValueError, match="positive"):
            config.validate()
    
    def test_validate_overlap_too_large(self):
        """Test validation fails when overlap >= chunk_size."""
        from src.config import ChunkingConfig
        
        config = ChunkingConfig()
        config.chunk_size = 100
        config.chunk_overlap = 100
        
        with pytest.raises(ValueError, match="less than"):
            config.validate()


class TestSettings:
    """Tests for main Settings class."""
    
    def test_settings_singleton(self):
        """Test settings is accessible."""
        from src.config import settings
        
        assert settings is not None
        assert hasattr(settings, "azure")
        assert hasattr(settings, "vectorstore")
        assert hasattr(settings, "chunking")
    
    def test_is_development(self):
        """Test development mode detection."""
        from src.config import Settings
        
        settings = Settings()
        settings.app_env = "development"
        assert settings.is_development is True
        assert settings.is_production is False
    
    def test_is_production(self):
        """Test production mode detection."""
        from src.config import Settings
        
        settings = Settings()
        settings.app_env = "production"
        assert settings.is_production is True
        assert settings.is_development is False
