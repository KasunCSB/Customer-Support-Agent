# Customer Support Agent 🤖

A RAG-based (Retrieval-Augmented Generation) AI customer support agent built with Azure OpenAI and ChromaDB.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🌟 Features

- **RAG Pipeline**: Retrieval-augmented generation for accurate, grounded responses
- **Azure OpenAI Integration**: Uses GPT-4o-mini for chat and text-embedding-3-large for embeddings
- **ChromaDB Vector Store**: Local, persistent vector storage for development
- **Token-Aware Chunking**: Smart document splitting with tiktoken
- **CLI Interface**: Full-featured command-line interface for all operations
- **Conversation Memory**: Multi-turn conversation support
- **Source Citations**: Responses include references to source documents
- **Extensible Architecture**: SOLID principles for easy customization

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Interface                             │
│                     (src/cli.py)                                 │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       RAG Pipeline                               │
│                  (src/pipeline/rag_pipeline.py)                  │
│  ┌───────────────┐    ┌────────────────┐    ┌────────────────┐  │
│  │   Retriever   │───▶│  Context Asm.  │───▶│   LLM Reader   │  │
│  └───────────────┘    └────────────────┘    └────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                                           │
         ▼                                           ▼
┌─────────────────────┐                 ┌─────────────────────────┐
│   Vector Store      │                 │    Azure OpenAI         │
│   (ChromaDB)        │                 │    (GPT-4o-mini)        │
│ src/core/vectorstore│                 │    src/core/llm.py      │
└─────────────────────┘                 └─────────────────────────┘
         ▲
         │
┌─────────────────────┐
│  Embedding Provider │
│  (text-embedding-   │
│   3-large)          │
│ src/core/embeddings │
└─────────────────────┘
```

## 📁 Project Structure

```
Customer-Support-Agent/
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── README.md             # This file
├── requirements.txt      # Python dependencies
├── pyproject.toml        # Project configuration
├── data/
│   ├── raw/              # Original documents
│   ├── processed/        # Processed data
│   └── samples/          # Sample datasets
│       └── sample_faq.jsonl
├── docs/
│   ├── ARCHITECTURE.md   # Detailed architecture docs
│   └── CONTRIBUTING.md   # Contribution guidelines
├── src/
│   ├── __init__.py
│   ├── cli.py            # Command-line interface
│   ├── config.py         # Configuration management
│   ├── ingestion.py      # Document ingestion
│   ├── logger.py         # Logging setup
│   ├── core/
│   │   ├── __init__.py
│   │   ├── embeddings.py # Embedding providers
│   │   ├── llm.py        # LLM providers
│   │   └── vectorstore.py # Vector store implementations
│   └── pipeline/
│       ├── __init__.py
│       ├── chunker.py    # Text chunking
│       ├── retriever.py  # Document retrieval
│       └── rag_pipeline.py # RAG orchestration
├── tests/
│   ├── __init__.py
│   ├── conftest.py       # Pytest fixtures
│   ├── test_chunker.py
│   ├── test_config.py
│   └── test_vectorstore.py
└── vectorstore/          # ChromaDB persistence (gitignored)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Azure OpenAI resource with deployments:
  - `chat-model` (GPT-4o-mini)
  - `embedding-model` (text-embedding-3-large)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/customer-support-agent.git
   cd customer-support-agent
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Azure OpenAI credentials
   ```

5. **Test configuration**
   ```bash
   python -m src.cli test
   ```

### Basic Usage

1. **Ingest documents**
   ```bash
   # Ingest sample FAQ data
   python -m src.cli ingest data/samples/sample_faq.jsonl
   
   # Ingest a directory of documents
   python -m src.cli ingest data/documents/ --recursive
   ```

2. **Ask questions**
   ```bash
   python -m src.cli query "How do I reset my password?"
   
   # With streaming output
   python -m src.cli query "What's your return policy?" --stream
   ```

3. **Interactive chat**
   ```bash
   python -m src.cli chat
   
   # Commands in chat mode:
   # /clear  - Clear conversation history
   # /stats  - Show statistics
   # /quit   - Exit chat
   ```

4. **View statistics**
   ```bash
   python -m src.cli stats
   ```

## 📖 CLI Reference

### Commands

| Command | Description |
|---------|-------------|
| `ingest <path>` | Ingest documents from file or directory |
| `query <question>` | Ask a single question |
| `chat` | Start interactive chat session |
| `stats` | Show system statistics |
| `test` | Test system configuration |
| `clear` | Clear the vector store |

### Options

```bash
# Global options
--verbose, -v     Enable verbose output

# Ingest options
--recursive, -r   Process directories recursively (default: True)

# Query options
--top-k, -k       Number of documents to retrieve (default: 5)
--stream, -s      Stream the response
--show-sources    Show source documents

# Chat options
--stream, -s      Stream responses

# Clear options
--force, -f       Skip confirmation prompt
```

## ⚙️ Configuration

All configuration is done through environment variables. See `.env.example` for all options:

```bash
# Azure OpenAI
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_CHAT_DEPLOYMENT=chat-model
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=embedding-model

# Chunking
CHUNK_SIZE_TOKENS=1000
CHUNK_OVERLAP_TOKENS=200

# Retrieval
RETRIEVAL_TOP_K=5
CONTEXT_TOKEN_BUDGET=3000

# LLM
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=512
```

## 🧪 Testing

Run tests with pytest:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run specific test file
pytest tests/test_chunker.py -v
```

## 🔧 Development

### Code Style

This project uses:
- **Black** for code formatting
- **isort** for import sorting
- **Pylint** for linting
- **mypy** for type checking

```bash
# Format code
black src/ tests/
isort src/ tests/

# Check types
mypy src/
```

### Adding New Features

The codebase follows SOLID principles:

- **Single Responsibility**: Each module has one purpose
- **Open/Closed**: Use interfaces for extension
- **Liskov Substitution**: Implementations are interchangeable
- **Interface Segregation**: Small, focused interfaces
- **Dependency Inversion**: Depend on abstractions

To add a new embedding provider:

```python
from src.core.embeddings import EmbeddingProvider

class MyEmbeddingProvider(EmbeddingProvider):
    @property
    def dimension(self) -> int:
        return 768
    
    def embed(self, text: str) -> List[float]:
        # Your implementation
        pass
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        # Your implementation
        pass
```

## 📊 Data Formats

### Supported Input Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| Text | `.txt` | Plain text files |
| Markdown | `.md` | Markdown documents |
| JSON | `.json` | JSON with `text`/`content` field |
| JSON Lines | `.jsonl` | One JSON object per line |

### JSONL Format Example

```json
{"id": "faq_001", "question": "How do I reset my password?", "answer": "Click 'Forgot Password'...", "category": "account"}
{"id": "faq_002", "question": "What payment methods?", "answer": "We accept Visa, MasterCard...", "category": "billing"}
```

## 🛣️ Roadmap

- [ ] **Phase 1**: Basic RAG chatbot (current)
- [ ] **Phase 2**: Agent with function calling
- [ ] **Phase 3**: Voice interface integration
- [ ] **Phase 4**: Web UI with Streamlit/Gradio
- [ ] **Phase 5**: Production deployment

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangChain](https://github.com/langchain-ai/langchain) for RAG patterns
- [ChromaDB](https://github.com/chroma-core/chroma) for vector storage
- [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service) for LLM and embeddings
