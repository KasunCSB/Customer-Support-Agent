"""
FastAPI Backend Server

Exposes the RAG pipeline functionality as REST API endpoints
for the Next.js UI to consume.
"""

import asyncio
import json
import os
import sys
import random
import time
import re
from collections import defaultdict
from typing import AsyncGenerator, Optional, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.pipeline.rag_pipeline import RAGPipeline
from src.logger import get_logger
from src.messages import msg

logger = get_logger(__name__)


 


# Pydantic models for API
class QueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    confidence: Optional[float] = None


class StatsResponse(BaseModel):
    document_count: int
    collection_name: str
    chunk_size: int
    environment: str


class TestResult(BaseModel):
    name: str
    passed: bool
    message: Optional[str] = None
    duration: Optional[int] = None


class TestResponse(BaseModel):
    results: list[TestResult]


# Global pipeline instance
pipeline: Optional[RAGPipeline] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources."""
    global pipeline
    
    # Initialize on startup
    # RAGPipeline() initializes with default components
    pipeline = RAGPipeline()
    logger.info(f"Pipeline initialized with {pipeline.document_count} documents")
    
    yield
    
    # Cleanup on shutdown
    pipeline = None


# Rate limiting middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    Limits requests per IP address within a time window.
    """
    
    def __init__(self, app, requests_limit: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.request_counts: Dict[str, list] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health check
        if request.url.path == "/api/health":
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        
        # Clean old timestamps and check rate limit
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        
        # Remove expired timestamps
        self.request_counts[client_ip] = [
            ts for ts in self.request_counts[client_ip] if ts > cutoff_time
        ]
        
        # Check if rate limited
        if len(self.request_counts[client_ip]) >= self.requests_limit:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": msg("error.rate_limited"),
                    "retry_after": self.window_seconds
                },
                headers={"Retry-After": str(self.window_seconds)}
            )
        
        # Record this request
        self.request_counts[client_ip].append(current_time)
        
        return await call_next(request)


# Create FastAPI app
app = FastAPI(
    title="Customer Support Agent API",
    description="REST API for RAG-based customer support",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    requests_limit=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window,
)

# CORS middleware - uses configurable origins from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_pipeline() -> RAGPipeline:
    """Get the pipeline instance."""
    if pipeline is None:
        raise HTTPException(status_code=503, detail=msg("error.pipeline_not_ready"))
    return pipeline


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/welcome")
@app.get("/api/welcome")
async def welcome_message():
    """Return a short welcome message for the UI hero."""
    return {"message": msg("welcome.message")}


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Single-shot query without conversation context."""
    try:
        pipe = get_pipeline()
        
        # Check if we have documents
        if pipe.document_count == 0:
            logger.warning("Query attempted with empty vector store")
        
        result = await asyncio.to_thread(
            pipe.query,
            request.query,
            top_k=request.top_k,
        )
        
        return QueryResponse(
            answer=result.answer,
            sources=[
                {
                    "content": s.get("text", s.get("content", "")),
                    "source": s.get("source", ""),
                    "score": s.get("score"),
                }
                for s in result.sources
            ],
            confidence=result.tokens_used.get("total_tokens", 0) if result.tokens_used else 0,
        )
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat with conversation context, optionally streaming."""
    try:
        pipe = get_pipeline()
        
        if request.stream:
            # Streaming response using proper async pattern
            async def generate() -> AsyncGenerator[str, None]:
                async_queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
                error_holder: list[Exception] = []
                
                async def stream_producer():
                    """Run the sync stream_query in a thread and push tokens to async queue."""
                    try:
                        # Run sync iterator in thread pool
                        def iterate_stream():
                            tokens = []
                            for token in pipe.stream_query(
                                request.message,
                                include_history=True,
                                session_id=request.session_id,
                            ):
                                tokens.append(token)
                            return tokens
                        
                        tokens = await asyncio.to_thread(iterate_stream)
                        for token in tokens:
                            await async_queue.put(token)
                    except Exception as e:
                        error_holder.append(e)
                    finally:
                        await async_queue.put(None)  # Signal completion
                
                # Start producer task
                producer_task = asyncio.create_task(stream_producer())
                
                try:
                    # Yield tokens as they arrive
                    while True:
                        try:
                            token = await asyncio.wait_for(async_queue.get(), timeout=60.0)
                            if token is None:
                                break
                            data = json.dumps({
                                "type": "chunk",
                                "content": token,
                            })
                            yield f"data: {data}\n\n"
                        except asyncio.TimeoutError:
                            logger.warning("Streaming timeout - no token received in 60s")
                            break
                    
                    # Ensure producer is done
                    await producer_task
                    
                    # Check for errors
                    if error_holder:
                        raise error_holder[0]
                    
                    # Send completion signal
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    
                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    error_data = json.dumps({
                        "type": "error",
                        "error": str(e),
                    })
                    yield f"data: {error_data}\n\n"
                finally:
                    # Cancel producer if still running
                    if not producer_task.done():
                        producer_task.cancel()
                        try:
                            await producer_task
                        except asyncio.CancelledError:
                            pass
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            # Non-streaming response
            result = await asyncio.to_thread(
                pipe.chat,
                request.message,
                None,
                request.session_id,
            )
            
            return {
                "answer": result.answer,
                "sources": [
                    {
                        "source": s.get("source", ""),
                        "content": s.get("text", s.get("content", "")),
                    }
                    for s in result.sources
                ],
                "session_id": request.session_id,
            }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get system statistics."""
    try:
        pipe = get_pipeline()
        
        # Get stats from vector store using the public get_stats() method
        doc_count = 0
        collection = "default"
        
        if hasattr(pipe, 'vector_store') and pipe.vector_store:
            try:
                vs_stats = pipe.vector_store.get_stats()  # type: ignore[attr-defined]
                doc_count = vs_stats.get("document_count", 0)
                collection = vs_stats.get("collection_name", "default")
            except Exception as e:
                logger.warning(f"Could not get vector store stats: {e}")
                # Fallback to direct count if get_stats fails
                try:
                    doc_count = pipe.vector_store.count()
                    collection = pipe.vector_store.collection_name if hasattr(pipe.vector_store, 'collection_name') else "default"  # type: ignore[attr-defined]
                except Exception:
                    pass
        
        return StatsResponse(
            document_count=doc_count,
            collection_name=collection,
            chunk_size=settings.chunking.chunk_size,
            environment=settings.app_env,
        )
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test", response_model=TestResponse)
async def run_tests():
    """Run system tests."""
    import time
    results = []
    
    # Test 1: Pipeline initialization
    start = time.perf_counter()
    try:
        pipe = get_pipeline()
        duration = int((time.perf_counter() - start) * 1000)
        results.append(TestResult(
            name="Pipeline Initialization",
            passed=pipe is not None,
            duration=duration,
        ))
    except Exception as e:
        results.append(TestResult(
            name="Pipeline Initialization",
            passed=False,
            message=str(e),
        ))
    
    # Test 2: Vector store connection
    start = time.perf_counter()
    try:
        pipe = get_pipeline()
        if hasattr(pipe, 'vector_store') and pipe.vector_store:
            # Use the public get_stats method
            vs_stats = pipe.vector_store.get_stats()  # type: ignore[attr-defined]
        duration = int((time.perf_counter() - start) * 1000)
        results.append(TestResult(
            name="Vector Store Connection",
            passed=True,
            duration=duration,
        ))
    except Exception as e:
        results.append(TestResult(
            name="Vector Store Connection",
            passed=False,
            message=str(e),
        ))
    
    # Test 3: Embedding generation (test before LLM since it's faster)
    start = time.perf_counter()
    try:
        pipe = get_pipeline()
        # Use the embedding provider from the pipeline
        embeddings_provider = pipe.embedding_provider
        _ = await asyncio.to_thread(embeddings_provider.embed, "test")
        duration = int((time.perf_counter() - start) * 1000)
        results.append(TestResult(
            name="Embedding Generation",
            passed=True,
            duration=duration,
        ))
    except Exception as e:
        results.append(TestResult(
            name="Embedding Generation",
            passed=False,
            message=str(e),
        ))
    
    # Test 4: LLM connectivity
    start = time.perf_counter()
    try:
        pipe = get_pipeline()
        _ = await asyncio.to_thread(pipe.query, "test", top_k=1)
        duration = int((time.perf_counter() - start) * 1000)
        results.append(TestResult(
            name="LLM Connectivity",
            passed=True,
            duration=duration,
        ))
    except Exception as e:
        results.append(TestResult(
            name="LLM Connectivity",
            passed=False,
            message=str(e),
        ))
    
    return TestResponse(results=results)
@app.post("/api/memory/clear")
async def clear_memory():
    """Clear conversation memory."""
    try:
        pipe = get_pipeline()
        pipe.clear_memory()
        return {"success": True, "message": msg("memory.cleared")}
    except Exception as e:
        logger.error(f"Memory clear error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None


@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech and return audio as MP3.
    Uses Azure Speech Services.
    """
    try:
        import azure.cognitiveservices.speech as speechsdk
        import io
        
        if not settings.speech.is_configured:
            raise HTTPException(status_code=503, detail=msg("error.speech_not_configured"))
        
        # Create speech config
        speech_config = speechsdk.SpeechConfig(
            subscription=settings.speech.api_key,
            region=settings.speech.region
        )
        
        # Set voice
        voice = request.voice or settings.speech.voice_name
        speech_config.speech_synthesis_voice_name = voice
        
        # Use MP3 format for web playback
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
        )
        
        # Create synthesizer without audio output (we'll capture the data)
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=None  # No audio output, we capture the stream
        )
        
        # Synthesize
        result = await asyncio.to_thread(
            lambda: synthesizer.speak_text_async(request.text).get()
        )
        
        # Type checker doesn't recognize Azure SDK's dynamic attributes
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:  # type: ignore[union-attr]
            # Return audio as streaming response
            audio_data = result.audio_data  # type: ignore[union-attr]
            return StreamingResponse(
                io.BytesIO(audio_data),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": "inline",
                    "Content-Length": str(len(audio_data)),
                }
            )
        elif result.reason == speechsdk.ResultReason.Canceled:  # type: ignore[union-attr]
            cancellation = result.cancellation_details  # type: ignore[union-attr]
            logger.error(f"TTS canceled: {cancellation.error_details}")
            raise HTTPException(status_code=500, detail=f"TTS failed: {cancellation.reason}")
        else:
            raise HTTPException(status_code=500, detail=msg("error.tts_failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
