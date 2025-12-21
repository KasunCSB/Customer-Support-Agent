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
import sys
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
        
        if path.is_file():
            result = ingester.ingest_file(path)
        elif path.is_dir():
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
                
                # Process query
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
        default=True,
        help="Process directories recursively (default: True)"
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
