<div align="center">
  <svg width="160" height="160" viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Animated orb logo">
    <defs>
      <radialGradient id="orb-base" cx="30%" cy="25%" r="70%">
        <stop offset="0%" stop-color="#E879F9" />
        <stop offset="35%" stop-color="#A855F7" />
        <stop offset="60%" stop-color="#6366F1" />
        <stop offset="85%" stop-color="#3B82F6" />
        <stop offset="100%" stop-color="#06B6D4" />
      </radialGradient>
      <radialGradient id="orb-accent-1" cx="70%" cy="30%" r="55%">
        <stop offset="0%" stop-color="#F0ABFC" stop-opacity="0.9" />
        <stop offset="50%" stop-color="#C084FC" stop-opacity="0.5" />
        <stop offset="100%" stop-color="#818CF8" stop-opacity="0" />
      </radialGradient>
      <radialGradient id="orb-accent-2" cx="25%" cy="70%" r="55%">
        <stop offset="0%" stop-color="#67E8F9" stop-opacity="0.8" />
        <stop offset="55%" stop-color="#22D3EE" stop-opacity="0.4" />
        <stop offset="100%" stop-color="#2DD4BF" stop-opacity="0" />
      </radialGradient>
      <radialGradient id="orb-gloss" cx="32%" cy="18%" r="55%">
        <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0.5" />
        <stop offset="40%" stop-color="#FFFFFF" stop-opacity="0.2" />
        <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0" />
      </radialGradient>
      <radialGradient id="orb-depth" cx="50%" cy="50%" r="70%">
        <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0" />
        <stop offset="70%" stop-color="#FFFFFF" stop-opacity="0.08" />
        <stop offset="100%" stop-color="#000000" stop-opacity="0.25" />
      </radialGradient>
      <filter id="orb-glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="12" />
      </filter>
    </defs>
    <g>
      <circle cx="100" cy="100" r="78" fill="url(#orb-base)" />
      <circle cx="100" cy="100" r="78" fill="url(#orb-accent-1)" />
      <circle cx="100" cy="100" r="78" fill="url(#orb-accent-2)" />
      <circle cx="100" cy="100" r="78" fill="url(#orb-gloss)" />
      <circle cx="100" cy="100" r="78" fill="url(#orb-depth)" />
      <circle cx="100" cy="100" r="86" fill="none" stroke="#FFFFFF" stroke-opacity="0.2" />
      <circle cx="100" cy="100" r="88" fill="none" stroke="#FFFFFF" stroke-opacity="0.08" />
      <animateTransform attributeName="transform" type="rotate" from="0 100 100" to="360 100 100" dur="48s" repeatCount="indefinite" />
    </g>
    <g filter="url(#orb-glow)" opacity="0.6">
      <circle cx="100" cy="100" r="92" fill="#A855F7">
        <animate attributeName="opacity" values="0.35;0.65;0.35" dur="6s" repeatCount="indefinite" />
      </circle>
    </g>
  </svg>
  <h1>Customer Support Agent</h1>
  <p><strong>LankaTel AI Support Assistant</strong></p>
  <p>RAG-first support with voice, actions, and a modern UI.</p>
  <p>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+" /></a>
    <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License" /></a>
    <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style: black" /></a>
  </p>
</div>

A RAG-based AI customer support agent built with Azure OpenAI and ChromaDB. It includes a FastAPI backend, a Next.js UI, and optional voice and admin workflows.

## Scenario

LankaTel is a conceptual internet service provider in Sri Lanka. This project is its AI support product: a complete customer support stack with a RAG knowledge brain, action-ready backend, and a modern UI. It ships with realistic telecom knowledge, supports chat and voice, and can handle guided workflows like ticket creation or service changes. Use it as a drop-in reference only.

## Features

- Retrieval-augmented generation with source citations
- Azure OpenAI chat and embedding deployments
- ChromaDB local vector store with persistence
- Token-aware chunking with tiktoken
- CLI for ingest, query, chat, voice, and realtime voice
- FastAPI backend API for the UI and external clients
- Next.js UI with chat, voice, tools, and admin console
- Agentic actions (tickets, subscriptions, balance) backed by MySQL
- Optional Azure Speech integration for STT/TTS
- Single-container Docker image with nginx reverse proxy

## Architecture

```
[Next.js UI] --> /api --> [FastAPI backend]
                        |-> [RAG pipeline] -> [ChromaDB]
                        |-> [Azure OpenAI]
                        |-> [MySQL] (actions, sessions, admin)
                        |-> [Azure Speech] (voice)
```

## Project Structure

```
Customer-Support-Agent/
  api_server.py              # FastAPI backend
  src/                       # Core pipeline, services, realtime voice
  ui/                        # Next.js frontend
  data/
    raw/                     # Raw JSONL knowledge files
    processed/               # Generated KB (gitignored)
  db/                        # MySQL schema + seed data
  docker/                    # Nginx + container entrypoint
  scripts/                   # Utilities (KB build, quota check)
  tests/                     # Pytest suite
  vectorstore/               # ChromaDB persistence (gitignored)
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+ (for the UI)
- Azure OpenAI deployments:
  - `chat-model` (GPT-4o-mini)
  - `embedding-model` (text-embedding-3-large)
- Optional: MySQL 8.x for actions/admin data
- Optional: Azure Speech for voice features

### Installation

1. Create a virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment
   ```bash
   cp .env.example .env
   # Edit .env with your Azure OpenAI credentials
   ```

4. (Optional) Initialize MySQL data
   ```bash
   mysql -u root -p < db/mysql_schema.sql
   ```

5. Test configuration
   ```bash
   python -m src.cli test
   ```

### Basic Usage

1. Ingest documents
   ```bash
   # Ingest the bundled Lankatel data (auto-builds a processed KB)
   python -m src.cli ingest data/raw/lankatel

   # Ingest a directory of documents
   python -m src.cli ingest data/documents/ --recursive
   ```

2. Ask questions
   ```bash
   python -m src.cli query "How do I reset my password?"
   python -m src.cli query "What is my plan balance?" --stream
   ```

3. Interactive chat
   ```bash
   python -m src.cli chat
   ```

4. Voice modes (optional)
   ```bash
   python -m src.cli voice-chat
   python -m src.cli realtime
   ```

## Run the API Server and UI

1. Start the backend
   ```bash
   python api_server.py
   ```

2. Start the UI
   ```bash
   cd ui
   cp .env.example .env.local
   npm install
   npm run dev
   ```

The UI will be available at `http://localhost:3000` and the backend at `http://localhost:8000`.

## CLI Reference

| Command | Description |
|---------|-------------|
| `ingest <path>` | Ingest documents from file or directory |
| `query <question>` | Ask a single question |
| `chat` | Start interactive chat session |
| `voice-chat` | Start turn-based voice chat |
| `realtime` | Start realtime full-duplex voice chat |
| `stats` | Show system statistics |
| `test` | Test system configuration |
| `clear` | Clear the vector store |

## Data Formats

Supported input formats:

| Format | Extension | Description |
|--------|-----------|-------------|
| Text | `.txt` | Plain text files |
| Markdown | `.md` | Markdown documents |
| JSON | `.json` | JSON with `text` or `content` field |
| JSON Lines | `.jsonl` | One JSON object per line |

JSONL example:

```json
{"id": "faq_001", "question": "How do I reset my password?", "answer": "Click 'Forgot Password'...", "category": "account"}
{"id": "faq_002", "question": "What payment methods?", "answer": "We accept Visa, MasterCard...", "category": "billing"}
```

To normalize the bundled Lankatel data manually:

```bash
python scripts/build_processed_kb.py
```

## Configuration

All configuration is done via environment variables. See `.env.example` and `ui/.env.example` for the full list. Common settings:

```bash
# Azure OpenAI
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_CHAT_DEPLOYMENT=chat-model
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=embedding-model

# Vector store
VECTORSTORE_DIR=./vectorstore
VECTORSTORE_COLLECTION=support_docs

# Optional services
DB_URL=mysql+pymysql://user:password@localhost/ltagent
AZURE_SPEECH_API_KEY=...
AZURE_SPEECH_REGION=eastus

# Admin console
ADMIN_USERNAME=ltadmin
ADMIN_PASSWORD=change_me_strong
ADMIN_SECRET=change_me_secret
```

## Testing

```bash
pytest tests/ -v
```

## Docker (Single-container frontend + backend)

This repository includes a `Dockerfile` that builds the Next.js UI and packages the Python backend into a single container. Nginx is used inside the container to reverse-proxy:

- Requests under `/api/` are forwarded to the Python backend (uvicorn) on port `8000`
- All other requests are forwarded to the Next.js server on port `3000`

Build and run locally:

```bash
docker build -t customer-support-agent:latest .
docker run -p 80:80 customer-support-agent:latest
```

Notes on Azure deployment:

- Push the image to a container registry (ACR or Docker Hub) and point your Azure Web App for Containers or Azure Container Instance to the image.
- Azure expects a single HTTP port (80) to be served by the container; the image exposes port 80 and uses nginx as the entrypoint.

## Contributing

Contributions are welcome. Please open a PR with a clear description of the change.

## License

MIT. See [LICENSE](LICENSE).

## Acknowledgments

- LangChain for RAG patterns
- ChromaDB for vector storage
- Azure OpenAI for LLMs and embeddings
