#!/usr/bin/env python3
"""
Customer Support Agent - Command Line Interface

A comprehensive CLI for interacting with the RAG-based customer support agent.

Commands:
    ingest      - Ingest documents into the vector store
    query       - Ask a single question
    chat        - Start an interactive chat session
    voice-chat  - Start an interactive voice chat session
    stats       - Show system statistics
    clear       - Clear the vector store

Usage:
    python -m src.cli ingest data/samples/sample_faq.jsonl
    python -m src.cli query "How do I reset my password?"
    python -m src.cli chat
    python -m src.cli voice-chat
    python -m src.cli stats

For help on a specific command:
    python -m src.cli <command> --help
"""

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.logger import init_logging, get_logger
from src.config import settings

# Initialize logging
init_logging()
logger = get_logger(__name__)


def cmd_ingest(args: argparse.Namespace) -> int:
    """
    Ingest documents into the vector store.
    
    Supports files (.txt, .md, .json, .jsonl) and directories.
    """
    from src.ingestion import DocumentIngester
    
    print(f"\n📂 Ingesting: {args.path}")
    print("-" * 50)
    
    try:
        ingester = DocumentIngester()
        path = Path(args.path)

        def build_processed_kb_for_lankatel(raw_dir: Path) -> Optional[Path]:
            """Build data/processed/lankatel/kb.jsonl from data/raw/lankatel/*.jsonl.

            This matches the previously recommended workflow but runs automatically
            when the user ingests the Lankatel raw directory.
            """

            def to_text(item: dict) -> Optional[str]:
                def _as_lines(prefix: str, values: list[str]) -> str:
                    cleaned = [v.strip() for v in values if isinstance(v, str) and v.strip()]
                    if not cleaned:
                        return ""
                    return prefix + "\n" + "\n".join(f"- {v}" for v in cleaned)

                # 1) Direct text fields
                text = item.get("text") or item.get("content") or item.get("body")
                if isinstance(text, str) and text.strip():
                    header = []
                    for k in ("topic", "name", "title"):
                        v = item.get(k)
                        if isinstance(v, str) and v.strip():
                            header.append(f"{k.capitalize()}: {v.strip()}")
                    return ("\n".join(header) + ("\n\n" if header else "") + text.strip()).strip()

                # 2) FAQ style
                q = item.get("question")
                a = item.get("answer")
                if isinstance(q, str) or isinstance(a, str):
                    q_s = (q or "").strip() if isinstance(q, str) else ""
                    a_s = (a or "").strip() if isinstance(a, str) else ""
                    if q_s or a_s:
                        return f"Question: {q_s}\n\nAnswer: {a_s}".strip()

                # 3) Common knowledge schemas
                description = item.get("description")
                if isinstance(description, str) and description.strip():
                    header = []
                    for k in ("topic", "name", "service_id", "package_id", "channel", "category"):
                        v = item.get(k)
                        if isinstance(v, str) and v.strip():
                            header.append(f"{k.replace('_', ' ').title()}: {v.strip()}")
                        elif isinstance(v, (int, float, bool)):
                            header.append(f"{k.replace('_', ' ').title()}: {v}")
                    return ("\n".join(header) + ("\n\n" if header else "") + description.strip()).strip()

                scenario = item.get("scenario")
                resolution = item.get("resolution")
                if isinstance(scenario, str) or isinstance(resolution, str):
                    s = scenario.strip() if isinstance(scenario, str) else ""
                    r = resolution.strip() if isinstance(resolution, str) else ""
                    topic = item.get("topic")
                    t = topic.strip() if isinstance(topic, str) else ""
                    parts = []
                    if t:
                        parts.append(f"Topic: {t}")
                    if s:
                        parts.append(f"Scenario: {s}")
                    if r:
                        parts.append(f"Resolution: {r}")
                    if parts:
                        return "\n\n".join(parts).strip()

                variants = item.get("variants")
                if isinstance(variants, list):
                    block = _as_lines("Variants:", [str(v) for v in variants])
                    key = item.get("key")
                    k = key.strip() if isinstance(key, str) else ""
                    if block:
                        return (f"Message Key: {k}\n\n{block}" if k else block).strip()

                messages = item.get("messages")
                if isinstance(messages, list) and messages:
                    lines: list[str] = []
                    for m in messages:
                        if not isinstance(m, dict):
                            continue
                        role = m.get("role")
                        content = m.get("content")
                        if isinstance(role, str) and isinstance(content, str) and content.strip():
                            lines.append(f"{role.strip()}: {content.strip()}")
                    if lines:
                        return "\n".join(lines).strip()

                # 4) Generic fallback: flatten primitives into key: value lines
                pairs: list[str] = []
                for k, v in item.items():
                    if k in {"id", "source", "index"}:
                        continue
                    if v is None:
                        continue
                    if isinstance(v, str) and v.strip():
                        pairs.append(f"{k.replace('_', ' ').title()}: {v.strip()}")
                    elif isinstance(v, (int, float, bool)):
                        pairs.append(f"{k.replace('_', ' ').title()}: {v}")
                    elif isinstance(v, list) and v:
                        simple = [str(x).strip() for x in v if str(x).strip()]
                        if simple:
                            pairs.append(f"{k.replace('_', ' ').title()}: {', '.join(simple)}")

                return "\n".join(pairs).strip() if pairs else None

            repo_root = project_root
            expected_raw = (repo_root / "data" / "raw" / "lankatel").resolve()
            if raw_dir.resolve() != expected_raw:
                return None

            jsonl_files = sorted(p for p in raw_dir.glob("*.jsonl") if p.is_file())
            if not jsonl_files:
                return None

            out_dir = repo_root / "data" / "processed" / "lankatel"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / "kb.jsonl"

            written = 0
            scanned_files = 0
            per_file_written: dict[str, int] = {}
            skipped_invalid_json = 0
            skipped_no_text = 0
            with out_file.open("w", encoding="utf-8") as out:
                for src in jsonl_files:
                    scanned_files += 1
                    file_written = 0
                    with src.open("r", encoding="utf-8") as f:
                        for i, line in enumerate(f):
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                item = json.loads(line)
                            except json.JSONDecodeError:
                                skipped_invalid_json += 1
                                continue

                            text = to_text(item)
                            if not text:
                                skipped_no_text += 1
                                continue

                            rec = {
                                "id": item.get("id") or f"{src.stem}_{i:06d}",
                                "text": text,
                                "source": src.name,
                            }

                            for key in ("category", "topic"):
                                val = item.get(key)
                                if isinstance(val, str) and val.strip():
                                    rec[key] = val.strip()

                            tags = item.get("tags")
                            if isinstance(tags, list):
                                tags_str = ",".join(str(t).strip() for t in tags if str(t).strip())
                                if tags_str:
                                    rec["tags"] = tags_str

                            for k, v in item.items():
                                if k in rec or k in {"text", "content", "body", "question", "answer", "tags"}:
                                    continue
                                if isinstance(v, (str, int, float, bool)):
                                    rec[k] = v

                            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                            written += 1
                            file_written += 1

                    per_file_written[src.name] = file_written

            if written:
                print(f"🧱 Built processed KB: {out_file} ({written} records)")
                print(f"📄 Scanned {scanned_files} JSONL files from {raw_dir}")

                zero_files = [name for name, n in per_file_written.items() if n == 0]
                if zero_files:
                    preview = ", ".join(zero_files[:8])
                    suffix = "" if len(zero_files) <= 8 else f" (+{len(zero_files) - 8} more)"
                    print(
                        "ℹ️ Files with 0 KB records (no text/content/body or question/answer fields): "
                        f"{preview}{suffix}"
                    )

                if skipped_invalid_json or skipped_no_text:
                    parts = []
                    if skipped_invalid_json:
                        parts.append(f"{skipped_invalid_json} invalid JSON lines")
                    if skipped_no_text:
                        parts.append(f"{skipped_no_text} lines without supported text fields")
                    print("ℹ️ Skipped: " + ", ".join(parts))
                return out_file

            return None
        
        if path.is_file():
            result = ingester.ingest_file(path)
        elif path.is_dir():
            kb_file = build_processed_kb_for_lankatel(path)
            if kb_file is not None:
                result = ingester.ingest_file(kb_file)
            else:
                result = ingester.ingest_directory(path, recursive=args.recursive)
        else:
            print(f"❌ Path not found: {args.path}")
            return 1
        
        # Print results
        print(f"\n✅ Ingestion Complete!")
        print(f"   Documents processed: {result.documents_processed}")
        print(f"   Chunks created:      {result.chunks_created}")
        print(f"   Chunks ingested:     {result.chunks_ingested}")
        print(f"   Total in store:      {ingester.document_count}")
        
        if result.errors:
            print(f"\n⚠️  Errors ({len(result.errors)}):")
            for error in result.errors[:5]:
                print(f"   - {error}")
        
        return 0 if result.success else 1
        
    except Exception as e:
        print(f"❌ Ingestion failed: {e}")
        logger.exception("Ingestion error")
        return 1


def cmd_query(args: argparse.Namespace) -> int:
    """
    Ask a single question and get a response.
    """
    from src.pipeline.rag_pipeline import RAGPipeline
    
    question = args.question
    print(f"\n❓ Question: {question}")
    print("-" * 50)
    
    try:
        pipeline = RAGPipeline()
        
        if pipeline.document_count == 0:
            print("⚠️  No documents in vector store. Run 'ingest' first.")
            return 1
        
        # Get response
        if args.stream:
            print("\n💬 Answer: ", end="", flush=True)
            for token in pipeline.stream_query(question, top_k=args.top_k):
                print(token, end="", flush=True)
            print("\n")
        else:
            response = pipeline.query(question, top_k=args.top_k)
            print(f"\n💬 Answer:\n{response.answer}")
            
            if args.show_sources and response.sources:
                print(f"\n📚 Sources:")
                for src in response.sources:
                    print(f"   - {src.get('source', 'Unknown')}")
            
            if args.verbose:
                print(f"\n📊 Stats:")
                print(f"   Tokens used: {response.tokens_used.get('total_tokens', 'N/A')}")
                print(f"   Model: {response.model}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        logger.exception("Query error")
        return 1


def cmd_chat(args: argparse.Namespace) -> int:
    """
    Start an interactive chat session.
    """
    from src.pipeline.rag_pipeline import RAGPipeline
    
    print("\n" + "=" * 60)
    print("🤖 Customer Support Agent - Interactive Chat")
    print("=" * 60)
    print("Type your questions below. Commands:")
    print("  /clear  - Clear conversation history")
    print("  /stats  - Show statistics")
    print("  /quit   - Exit chat")
    print("-" * 60)
    
    try:
        pipeline = RAGPipeline()
        
        if pipeline.document_count == 0:
            print("⚠️  No documents in vector store. Run 'ingest' first.")
            return 1
        
        print(f"📚 Knowledge base: {pipeline.document_count} chunks loaded\n")

        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() == "/quit":
                    print("\n👋 Goodbye!")
                    break
                elif user_input.lower() == "/clear":
                    pipeline.clear_memory()
                    print("🗑️  Conversation history cleared.\n")
                    continue
                elif user_input.lower() == "/stats":
                    stats = pipeline.get_stats()
                    print(f"\n📊 Statistics:")
                    print(f"   Documents: {stats['document_count']}")
                    print(f"   Memory turns: {stats['memory_turns']}")
                    print()
                    continue

                # Process query (RAG)
                if args.stream:
                    print("Bot: ", end="", flush=True)
                    for token in pipeline.stream_query(user_input):
                        print(token, end="", flush=True)
                    print("\n")
                else:
                    response = pipeline.chat(user_input)
                    print(f"Bot: {response.answer}\n")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break
        
        return 0
        
    except Exception as e:
        print(f"❌ Chat failed: {e}")
        logger.exception("Chat error")
        return 1


def cmd_stats(args: argparse.Namespace) -> int:
    """
    Show system statistics.
    """
    from src.core.vectorstore import ChromaVectorStore
    
    print("\n📊 System Statistics")
    print("-" * 50)
    
    try:
        store = ChromaVectorStore()
        stats = store.get_stats()
        
        print(f"Vector Store:")
        print(f"  Collection:     {stats['collection_name']}")
        print(f"  Documents:      {stats['document_count']}")
        print(f"  Directory:      {stats['persist_directory']}")
        
        print(f"\nConfiguration:")
        print(f"  Chunk size:     {settings.chunking.chunk_size} tokens")
        print(f"  Chunk overlap:  {settings.chunking.chunk_overlap} tokens")
        print(f"  Retrieval top_k: {settings.retrieval.top_k}")
        print(f"  LLM temperature: {settings.llm.temperature}")
        print(f"  Environment:    {settings.app_env}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Failed to get stats: {e}")
        logger.exception("Stats error")
        return 1


def cmd_clear(args: argparse.Namespace) -> int:
    """
    Clear the vector store.
    """
    from src.core.vectorstore import ChromaVectorStore
    
    if not args.force:
        confirm = input("⚠️  This will delete all documents. Continue? [y/N]: ")
        if confirm.lower() != "y":
            print("Cancelled.")
            return 0
    
    try:
        store = ChromaVectorStore()
        count = store.count()
        store.clear()
        
        print(f"✅ Cleared {count} documents from vector store.")
        return 0
        
    except Exception as e:
        print(f"❌ Failed to clear: {e}")
        logger.exception("Clear error")
        return 1


def cmd_test(args: argparse.Namespace) -> int:
    """
    Test the system configuration and connections.
    """
    print("\n🔧 Testing System Configuration")
    print("-" * 50)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Configuration
    print("\n1. Configuration...")
    try:
        settings.validate_all()
        print("   ✅ Configuration valid")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Configuration error: {e}")
        tests_failed += 1
    
    # Test 2: Azure OpenAI Embeddings
    print("\n2. Azure OpenAI Embeddings...")
    try:
        from src.core.embeddings import AzureEmbeddingProvider
        provider = AzureEmbeddingProvider()
        embedding = provider.embed("test")
        assert len(embedding) == 3072, f"Expected 3072 dims, got {len(embedding)}"
        print(f"   ✅ Embeddings working (dim={len(embedding)})")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Embeddings error: {e}")
        tests_failed += 1
    
    # Test 3: Azure OpenAI Chat
    print("\n3. Azure OpenAI Chat...")
    try:
        from src.core.llm import AzureLLMProvider, Message
        llm = AzureLLMProvider()
        response = llm.chat([Message(role="user", content="Say 'test passed' in 2 words")])
        print(f"   ✅ Chat working: '{response.content[:50]}...'")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Chat error: {e}")
        tests_failed += 1
    
    # Test 4: Vector Store
    print("\n4. Vector Store (ChromaDB)...")
    try:
        from src.core.vectorstore import ChromaVectorStore
        store = ChromaVectorStore()
        count = store.count()
        print(f"   ✅ Vector store working ({count} documents)")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Vector store error: {e}")
        tests_failed += 1
    
    # Test 5: Chunker
    print("\n5. Text Chunker...")
    try:
        from src.pipeline.chunker import TextChunker
        chunker = TextChunker()
        chunks = chunker.chunk_text("This is a test. " * 100)
        print(f"   ✅ Chunker working ({len(chunks)} chunks created)")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Chunker error: {e}")
        tests_failed += 1
    
    # Test 6: Azure Speech (optional)
    print("\n6. Azure Speech Services...")
    try:
        if settings.speech.is_configured:
            from src.core.speech import SpeechService
            service = SpeechService()
            print(f"   ✅ Speech configured (voice={settings.speech.voice_name})")
            tests_passed += 1
        else:
            print("   ⏭️  Not configured (optional)")
    except Exception as e:
        print(f"   ❌ Speech error: {e}")
        tests_failed += 1
    
    # Summary
    print("\n" + "-" * 50)
    print(f"Results: {tests_passed} passed, {tests_failed} failed")
    
    return 0 if tests_failed == 0 else 1


def cmd_voice_chat(args: argparse.Namespace) -> int:
    """
    Start an interactive voice chat session.
    
    Uses Azure Speech Services for speech-to-text and text-to-speech.
    """
    from src.pipeline.rag_pipeline import RAGPipeline
    from src.core.speech import SpeechService
    
    print("\n" + "=" * 60)
    print("🎙️  Customer Support Agent - Voice Chat")
    print("=" * 60)
    print("Speak your questions. Say 'goodbye' or 'exit' to quit.")
    print("Press Ctrl+C to stop at any time.")
    print("-" * 60)
    
    try:
        # Initialize services
        pipeline = RAGPipeline()
        speech = SpeechService()
        
        if pipeline.document_count == 0:
            print("⚠️  No documents in vector store. Run 'ingest' first.")
            return 1
        
        print(f"📚 Knowledge base: {pipeline.document_count} chunks loaded")
        print(f"🔊 Voice: {settings.speech.voice_name}")
        print()
        
        # Greeting
        greeting = "Hello! I'm your customer support assistant. How can I help you today?"
        print(f"🤖 Bot: {greeting}")
        speech.speak(greeting)
        
        while True:
            try:
                # Listen for user speech
                print("\n🎤 Listening... (speak now)")
                user_text = speech.recognize_from_microphone()
                
                if not user_text:
                    print("   (no speech detected, try again)")
                    continue
                
                print(f"👤 You: {user_text}")
                
                # Check for exit commands
                exit_phrases = ["goodbye", "exit", "quit", "bye", "stop"]
                if any(phrase in user_text.lower() for phrase in exit_phrases):
                    farewell = "Goodbye! Have a great day!"
                    print(f"🤖 Bot: {farewell}")
                    speech.speak(farewell)
                    break
                
                # Get response from RAG pipeline
                print("🤔 Thinking...")
                response = pipeline.chat(user_text)
                
                # Speak the response
                print(f"🤖 Bot: {response.answer}")
                speech.speak(response.answer)
                
            except KeyboardInterrupt:
                print("\n\n👋 Voice chat interrupted.")
                break
        
        return 0
        
    except Exception as e:
        print(f"❌ Voice chat failed: {e}")
        logger.exception("Voice chat error")
        return 1


def cmd_realtime_voice(args: argparse.Namespace) -> int:
    """
    Start an interactive real-time voice chat session.
    
    Uses the new full-duplex streaming architecture with:
    - Sub-500ms response latency
    - Barge-in support (interrupt while speaking)
    - Natural turn-taking with back-channels
    - Streaming STT/TTS for immediate response
    """
    import asyncio
    from src.realtime import RealtimeVoiceAgent, VoiceAgentConfig
    from src.realtime.voice_agent import print_banner
    from src.realtime.rag_engine import RealtimeRAGEngine
    from src.realtime.events import EventBus
    
    print_banner()
    
    try:
        # Check prerequisites
        if not settings.speech.is_configured:
            print("❌ Azure Speech not configured.")
            print("   Set AZURE_SPEECH_API_KEY and AZURE_SPEECH_REGION in .env")
            return 1
        
        # Check vector store
        from src.core.vectorstore import ChromaVectorStore
        store = ChromaVectorStore()
        if store.count() == 0:
            print("⚠️  No documents in vector store. Run 'ingest' first.")
            return 1
        
        print(f"📚 Knowledge base: {store.count()} chunks loaded")
        print(f"🔊 Voice: {settings.speech.voice_name}")
        print(f"🎤 Barge-in: {'enabled' if args.barge_in else 'disabled'}")
        print()
        
        # Create agent config
        config = VoiceAgentConfig(
            auto_greet=not args.no_greet,
            enable_barge_in=args.barge_in,
            idle_timeout_seconds=args.timeout,
        )
        
        if args.greeting:
            config.greeting = args.greeting
        
        # Create and run agent
        agent = RealtimeVoiceAgent(config)
        
        # Run async event loop
        asyncio.run(agent.run())
        
        # Print session stats
        print("\n" + "-" * 60)
        print("📊 Session Statistics:")
        print(f"   Turns completed: {agent.turn_count}")
        print(f"   Topics discussed: {', '.join(agent.session_topics) or 'none'}")
        stats = agent.stats
        if 'rag_stats' in stats:
            rag = stats['rag_stats']
            print(f"   RAG cache hit rate: {rag.get('cache_hit_rate', 0)*100:.0f}%")
        print()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n👋 Voice chat interrupted.")
        return 0
    except Exception as e:
        print(f"❌ Real-time voice chat failed: {e}")
        logger.exception("Real-time voice chat error")
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all commands."""
    parser = argparse.ArgumentParser(
        prog="customer-support-agent",
        description="RAG-based Customer Support AI Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Ingest documents:
    python -m src.cli ingest data/samples/sample_faq.jsonl
    python -m src.cli ingest data/documents/ --recursive

  Ask a question:
    python -m src.cli query "How do I reset my password?"
    python -m src.cli query "What's your return policy?" --stream

  Interactive chat:
    python -m src.cli chat
    python -m src.cli chat --stream

  System management:
    python -m src.cli stats
    python -m src.cli test
    python -m src.cli clear --force
        """
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Ingest command
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingest documents into the vector store"
    )
    ingest_parser.add_argument(
        "path",
        help="File or directory path to ingest"
    )
    ingest_parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        default=False,
        help="Process directories recursively"
    )
    ingest_parser.set_defaults(func=cmd_ingest)
    
    # Query command
    query_parser = subparsers.add_parser(
        "query",
        help="Ask a single question"
    )
    query_parser.add_argument(
        "question",
        help="Question to ask"
    )
    query_parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=5,
        help="Number of documents to retrieve (default: 5)"
    )
    query_parser.add_argument(
        "--stream", "-s",
        action="store_true",
        help="Stream the response"
    )
    query_parser.add_argument(
        "--show-sources",
        action="store_true",
        help="Show source documents"
    )
    query_parser.set_defaults(func=cmd_query)
    
    # Chat command
    chat_parser = subparsers.add_parser(
        "chat",
        help="Start an interactive chat session"
    )
    chat_parser.add_argument(
        "--stream", "-s",
        action="store_true",
        help="Stream responses"
    )
    chat_parser.set_defaults(func=cmd_chat)
    
    # Stats command
    stats_parser = subparsers.add_parser(
        "stats",
        help="Show system statistics"
    )
    stats_parser.set_defaults(func=cmd_stats)
    
    # Clear command
    clear_parser = subparsers.add_parser(
        "clear",
        help="Clear the vector store"
    )
    clear_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Skip confirmation prompt"
    )
    clear_parser.set_defaults(func=cmd_clear)
    
    # Test command
    test_parser = subparsers.add_parser(
        "test",
        help="Test system configuration"
    )
    test_parser.set_defaults(func=cmd_test)
    
    # Voice chat command (legacy turn-based)
    voice_parser = subparsers.add_parser(
        "voice-chat",
        help="Start an interactive voice chat session (turn-based)"
    )
    voice_parser.set_defaults(func=cmd_voice_chat)
    
    # Real-time voice chat command (new full-duplex)
    realtime_parser = subparsers.add_parser(
        "realtime",
        help="Start real-time voice chat (full-duplex, low-latency)"
    )
    realtime_parser.add_argument(
        "--no-greet",
        action="store_true",
        help="Skip automatic greeting"
    )
    realtime_parser.add_argument(
        "--greeting", "-g",
        type=str,
        help="Custom greeting message"
    )
    realtime_parser.add_argument(
        "--barge-in",
        action="store_true",
        default=True,
        help="Enable barge-in (interrupt while speaking)"
    )
    realtime_parser.add_argument(
        "--no-barge-in",
        action="store_false",
        dest="barge_in",
        help="Disable barge-in"
    )
    realtime_parser.add_argument(
        "--timeout", "-t",
        type=float,
        default=settings.realtime.idle_timeout_s,
        help=f"Idle timeout in seconds (default: {settings.realtime.idle_timeout_s})"
    )
    realtime_parser.set_defaults(func=cmd_realtime_voice)
    
    return parser


def main() -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
