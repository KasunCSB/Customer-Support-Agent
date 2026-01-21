"""
Configuration Management Module

This module handles all application configuration using environment variables
with sensible defaults. It follows the 12-factor app methodology for configuration.

Usage:
    from src.config import settings
    print(settings.AZURE_OPENAI_ENDPOINT)

Environment variables are loaded from .env file (if present) and can be
overridden by system environment variables.

SOLID Principles Applied:
- Single Responsibility: Only handles configuration loading and validation
- Open/Closed: New settings can be added without modifying existing code
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
# This should be called before accessing any environment variables
load_dotenv()


def get_env(key: str, default: str = "", required: bool = False) -> str:
    """
    Get an environment variable with optional default and validation.
    
    Args:
        key: The environment variable name
        default: Default value if not set
        required: If True, raises ValueError when not set
        
    Returns:
        The environment variable value or default
        
    Raises:
        ValueError: If required=True and the variable is not set
    """
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(f"Required environment variable '{key}' is not set")
    return value


def get_env_int(key: str, default: int) -> int:
    """Get an environment variable as integer."""
    return int(get_env(key, str(default)))


def get_env_float(key: str, default: float) -> float:
    """Get an environment variable as float."""
    return float(get_env(key, str(default)))


def get_env_bool(key: str, default: bool) -> bool:
    """Get an environment variable as boolean."""
    value = get_env(key, str(default)).lower()
    return value in ("true", "1", "yes", "on")


@dataclass
class AzureOpenAIConfig:
    """
    Azure OpenAI service configuration.
    
    Contains all settings needed to connect to Azure OpenAI services
    for both chat completions and embeddings.
    
    Attributes:
        api_key: Azure OpenAI API key
        endpoint: Azure OpenAI endpoint URL
        api_version: API version string
        chat_deployment: Deployment name for chat model
        embedding_deployment: Deployment name for embedding model
    """
    api_key: str = field(default_factory=lambda: get_env("AZURE_OPENAI_API_KEY"))
    endpoint: str = field(default_factory=lambda: get_env("AZURE_OPENAI_ENDPOINT"))
    api_version: str = field(default_factory=lambda: get_env("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"))
    chat_deployment: str = field(default_factory=lambda: get_env("AZURE_OPENAI_CHAT_DEPLOYMENT", "chat-model"))
    embedding_deployment: str = field(default_factory=lambda: get_env("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "embedding-model"))
    
    def validate(self) -> bool:
        """Validate that required Azure OpenAI settings are configured."""
        if not self.api_key:
            raise ValueError("AZURE_OPENAI_API_KEY is required")
        if not self.endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT is required")
        return True
    
    @property
    def embedding_url(self) -> str:
        """Get the full URL for embedding API calls."""
        base = self.endpoint.rstrip("/")
        return f"{base}/openai/deployments/{self.embedding_deployment}/embeddings?api-version={self.api_version}"
    
    @property
    def chat_url(self) -> str:
        """Get the full URL for chat completion API calls."""
        base = self.endpoint.rstrip("/")
        return f"{base}/openai/deployments/{self.chat_deployment}/chat/completions?api-version={self.api_version}"


@dataclass
class VectorStoreConfig:
    """
    Vector store configuration for ChromaDB.
    
    Attributes:
        directory: Path to persist vector store data
        collection: Name of the collection to use
    """
    directory: str = field(default_factory=lambda: get_env("VECTORSTORE_DIR", "./vectorstore"))
    collection: str = field(default_factory=lambda: get_env("VECTORSTORE_COLLECTION", "support_docs"))
    
    @property
    def path(self) -> Path:
        """Get the vector store directory as a Path object."""
        return Path(self.directory)


@dataclass
class ChunkingConfig:
    """
    Text chunking configuration for document processing.
    
    Attributes:
        chunk_size: Maximum tokens per chunk
        chunk_overlap: Number of overlapping tokens between chunks
    """
    chunk_size: int = field(default_factory=lambda: get_env_int("CHUNK_SIZE_TOKENS", 1000))
    chunk_overlap: int = field(default_factory=lambda: get_env_int("CHUNK_OVERLAP_TOKENS", 200))
    
    def validate(self) -> bool:
        """Validate chunking settings."""
        if self.chunk_size <= 0:
            raise ValueError("CHUNK_SIZE_TOKENS must be positive")
        if self.chunk_overlap < 0:
            raise ValueError("CHUNK_OVERLAP_TOKENS cannot be negative")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP_TOKENS must be less than CHUNK_SIZE_TOKENS")
        return True


@dataclass
class RetrievalConfig:
    """
    Retrieval configuration for RAG pipeline.
    
    Attributes:
        top_k: Number of chunks to retrieve per query
        context_token_budget: Maximum tokens to include in LLM context
    """
    top_k: int = field(default_factory=lambda: get_env_int("RETRIEVAL_TOP_K", 3))
    context_token_budget: int = field(default_factory=lambda: get_env_int("CONTEXT_TOKEN_BUDGET", 2000))


@dataclass
class LLMConfig:
    """
    LLM generation configuration.
    
    Attributes:
        temperature: Sampling temperature (0.0-1.0). Higher = more creative/natural
        max_tokens: Maximum tokens in response
        presence_penalty: Penalty for repeating topics (encourages diversity)
        frequency_penalty: Penalty for repeating exact phrases
    """
    temperature: float = field(default_factory=lambda: get_env_float("LLM_TEMPERATURE", 0.7))
    max_tokens: int = field(default_factory=lambda: get_env_int("LLM_MAX_TOKENS", 300))
    presence_penalty: float = field(default_factory=lambda: get_env_float("LLM_PRESENCE_PENALTY", 0.1))
    frequency_penalty: float = field(default_factory=lambda: get_env_float("LLM_FREQUENCY_PENALTY", 0.1))


@dataclass
class EmbeddingConfig:
    """
    Embedding generation configuration.
    
    Attributes:
        batch_size: Number of texts to embed per API call
        max_retries: Maximum retry attempts on failure
        enable_cache: Whether to cache embeddings
        delay_between_calls: Seconds to wait between API calls
    """
    batch_size: int = field(default_factory=lambda: get_env_int("EMBEDDING_BATCH_SIZE", 32))
    max_retries: int = field(default_factory=lambda: get_env_int("EMBEDDING_MAX_RETRIES", 5))
    enable_cache: bool = field(default_factory=lambda: get_env_bool("ENABLE_EMBEDDING_CACHE", True))
    delay_between_calls: float = field(default_factory=lambda: get_env_float("EMBEDDING_DELAY_BETWEEN_CALLS", 0.1))


@dataclass
class LoggingConfig:
    """
    Logging configuration.
    
    Attributes:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        file: Optional log file path
    """
    level: str = field(default_factory=lambda: get_env("LOG_LEVEL", "INFO"))
    file: Optional[str] = field(default_factory=lambda: get_env("LOG_FILE") or None)


@dataclass
class SpeechConfig:
    """
    Azure Speech Services configuration for voice features.
    
    Attributes:
        api_key: Azure Speech API key
        region: Azure region (e.g., eastus, westus2)
        language: Speech recognition language (BCP-47 format)
        voice_name: TTS voice name
        speech_timeout: Max seconds to wait for speech input
        silence_timeout: Seconds of silence to end recognition
    """
    api_key: str = field(default_factory=lambda: get_env("AZURE_SPEECH_API_KEY"))
    region: str = field(default_factory=lambda: get_env("AZURE_SPEECH_REGION", "eastus"))
    language: str = field(default_factory=lambda: get_env("SPEECH_LANGUAGE", "en-US"))
    voice_name: str = field(default_factory=lambda: get_env("SPEECH_VOICE_NAME", "en-US-JennyNeural"))
    speech_timeout: float = field(default_factory=lambda: get_env_float("SPEECH_TIMEOUT", 10.0))
    silence_timeout: float = field(default_factory=lambda: get_env_float("SILENCE_TIMEOUT", 1.5))
    
    def validate(self) -> bool:
        """Validate that required Speech settings are configured."""
        if not self.api_key:
            raise ValueError("AZURE_SPEECH_API_KEY is required for voice features")
        if not self.region:
            raise ValueError("AZURE_SPEECH_REGION is required for voice features")
        return True
    
    @property
    def is_configured(self) -> bool:
        """Check if speech services are configured."""
        return bool(self.api_key and self.region)


@dataclass
class DatabaseConfig:
    """
    Database configuration (MySQL via SQLAlchemy URL).
    """
    url: str = field(default_factory=lambda: get_env("DB_URL", "mysql+pymysql://user:password@localhost/ltagent"))


@dataclass
class EmailConfig:
    """
    Outbound email configuration for OTP/notifications.
    """
    smtp_host: str = field(default_factory=lambda: get_env("EMAIL_SMTP_HOST", ""))
    smtp_port: int = field(default_factory=lambda: get_env_int("EMAIL_SMTP_PORT", 587))
    smtp_username: str = field(default_factory=lambda: get_env("EMAIL_SMTP_USERNAME", ""))
    smtp_password: str = field(default_factory=lambda: get_env("EMAIL_SMTP_PASSWORD", ""))
    sender: str = field(default_factory=lambda: get_env("EMAIL_SENDER", "no-reply@kasunc.uk"))
    use_tls: bool = field(default_factory=lambda: get_env_bool("EMAIL_USE_TLS", True))
    enabled: bool = field(default_factory=lambda: get_env_bool("EMAIL_ENABLED", False))

    @property
    def is_configured(self) -> bool:
        """Check if email sending is configured."""
        return self.enabled and bool(self.smtp_host and self.smtp_username and self.smtp_password)


@dataclass
class RealtimeConfig:
    """
    Real-time voice agent configuration.
    
    Attributes:
        target_latency_ms: Target response latency in milliseconds
        end_silence_ms: Silence duration to detect turn end
        enable_barge_in: Allow user to interrupt agent
        enable_backchannels: Emit back-channel responses
        enable_speculative_rag: Start RAG on partial intent
        idle_timeout_s: Seconds of silence before prompting
        speaking_rate: TTS speaking rate (0.5 to 2.0)
    """
    target_latency_ms: int = field(default_factory=lambda: get_env_int("REALTIME_TARGET_LATENCY_MS", 500))
    end_silence_ms: int = field(default_factory=lambda: get_env_int("REALTIME_END_SILENCE_MS", 800))
    enable_barge_in: bool = field(default_factory=lambda: get_env_bool("REALTIME_ENABLE_BARGE_IN", True))
    enable_backchannels: bool = field(default_factory=lambda: get_env_bool("REALTIME_ENABLE_BACKCHANNELS", True))
    enable_speculative_rag: bool = field(default_factory=lambda: get_env_bool("REALTIME_SPECULATIVE_RAG", True))
    idle_timeout_s: float = field(default_factory=lambda: get_env_float("REALTIME_IDLE_TIMEOUT_S", 30.0))
    speaking_rate: float = field(default_factory=lambda: get_env_float("REALTIME_SPEAKING_RATE", 1.0))


@dataclass
class Settings:
    """
    Main settings container aggregating all configuration sections.
    
    This is the primary configuration interface for the application.
    Access via the singleton `settings` instance.
    
    Example:
        from src.config import settings
        
        # Access Azure settings
        settings.azure.validate()
        url = settings.azure.embedding_url
        
        # Access chunking settings
        chunk_size = settings.chunking.chunk_size
    """
    azure: AzureOpenAIConfig = field(default_factory=AzureOpenAIConfig)
    vectorstore: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    speech: SpeechConfig = field(default_factory=SpeechConfig)
    realtime: RealtimeConfig = field(default_factory=RealtimeConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    
    # Application-level settings
    app_env: str = field(default_factory=lambda: get_env("APP_ENV", "development"))
    enable_embedding_cache: bool = field(default_factory=lambda: get_env_bool("ENABLE_EMBEDDING_CACHE", True))
    
    # CORS configuration - comma-separated list of allowed origins
    cors_origins: list = field(default_factory=lambda: [
        origin.strip() for origin in 
        get_env("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
        if origin.strip()
    ])
    
    # Rate limiting configuration
    rate_limit_requests: int = field(default_factory=lambda: get_env_int("RATE_LIMIT_REQUESTS", 60))
    rate_limit_window: int = field(default_factory=lambda: get_env_int("RATE_LIMIT_WINDOW_SECONDS", 60))
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"
    
    def validate_all(self) -> bool:
        """
        Validate all configuration sections.
        
        Returns:
            True if all validations pass
            
        Raises:
            ValueError: If any validation fails
        """
        self.azure.validate()
        self.chunking.validate()
        return True


# Singleton settings instance
# Import this in other modules: from src.config import settings
settings = Settings()
