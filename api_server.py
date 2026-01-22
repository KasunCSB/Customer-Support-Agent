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
import datetime
import hmac
import hashlib
from collections import defaultdict
from typing import AsyncGenerator, Optional, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, EmailStr
from starlette.middleware.base import BaseHTTPMiddleware

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.pipeline.rag_pipeline import RAGPipeline
from src.logger import get_logger
from src.messages import msg
from src.services.auth import AuthService
from src.services.actions import ActionService
from src.services.email_client import EmailClient
from src.db import db

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


# Auth models
class OtpStartRequest(BaseModel):
    email: EmailStr


class OtpConfirmRequest(BaseModel):
    email: EmailStr
    code: str


class PhoneOtpStartRequest(BaseModel):
    phone: str


class PhoneOtpConfirmRequest(BaseModel):
    phone: str
    code: str


class SessionResponse(BaseModel):
    token: str
    expires_at: datetime.datetime
    user: dict


# Admin auth models
class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminUpdateRequest(BaseModel):
    data: dict


# Action models
class CreateTicketRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    subject: str
    description: str
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    idempotency_key: Optional[str] = None


class ServiceChangeRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    service_code: str
    idempotency_key: Optional[str] = None


# Global pipeline instance and services
pipeline: Optional[RAGPipeline] = None
auth_service = AuthService()
action_service = ActionService()
email_client = EmailClient()

# Admin table config (allowed columns for updates)
ADMIN_TABLES = {
    "users": {"display_name", "role", "status", "preferred_channel", "metadata", "external_id", "phone_e164", "email"},
    "services": {"name", "description", "category", "price", "currency", "validity_days", "metadata", "code"},
    "subscriptions": {"status", "activated_at", "expires_at", "external_ref", "metadata"},
    "tickets": {"subject", "description", "priority", "status", "assigned_to", "metadata", "closed_at"},
    "actions": {"status", "requires_confirmation", "params", "result", "error"},
}

# Admin session helpers
def _admin_sign(payload: str) -> str:
    secret = settings.admin.secret.encode("utf-8")
    return hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_admin_token(username: str) -> str:
    expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=settings.admin.cookie_ttl_hours)
    payload = f"{username}:{int(expiry.timestamp())}"
    signature = _admin_sign(payload)
    return f"{payload}.{signature}"


def verify_admin_token(token: str) -> Optional[str]:
    try:
        payload, signature = token.rsplit(".", 1)
    except ValueError:
        return None
    expected = _admin_sign(payload)
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        username, exp_ts = payload.split(":", 1)
        if int(exp_ts) < int(time.time()):
            return None
        return username
    except Exception:
        return None


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


def _is_admin_request(request: Request) -> bool:
    token = request.cookies.get(settings.admin.cookie_name)
    if not token:
        return False
    username = verify_admin_token(token)
    return bool(username and username == settings.admin.username)


def require_admin(request: Request):
    if not _is_admin_request(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


def _fetch_table(name: str, limit: int = 50, offset: int = 0):
    if name not in ADMIN_TABLES and name not in {
        "sessions",
        "verifications",
        "ticket_events",
        "action_events",
        "audit_logs",
    }:
        raise HTTPException(status_code=404, detail="Unknown table")
    if limit > 200:
        limit = 200
    sql = f"SELECT * FROM {name} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    return db.fetch_all(sql, {"limit": limit, "offset": offset})


def _update_table(name: str, row_id: str, data: dict):
    if name not in ADMIN_TABLES:
        raise HTTPException(status_code=400, detail="Updates not allowed for this table")
    allowed = ADMIN_TABLES[name]
    fields = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        raise HTTPException(status_code=400, detail="No allowed fields to update")
    set_clause = ", ".join(f"{col} = :{col}" for col in fields.keys())
    params = fields
    params["id"] = row_id
    sql = f"UPDATE {name} SET {set_clause} WHERE id = :id"
    db.execute(sql, params)
    return db.fetch_one(f"SELECT * FROM {name} WHERE id = :id", {"id": row_id})


def _admin_counts():
    counts = {}
    for tbl in [
        "users",
        "services",
        "subscriptions",
        "tickets",
        "actions",
        "sessions",
        "verifications",
        "audit_logs",
    ]:
        res = db.fetch_one(f"SELECT COUNT(*) as c FROM {tbl}")
        counts[tbl] = res["c"] if res else 0
    return counts


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

# Combine UI and admin CORS origins
_cors_origins = list(dict.fromkeys(settings.cors_origins + settings.admin.allowed_origins))

# Rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    requests_limit=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window,
)

# CORS middleware - uses configurable origins from settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
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


def _parse_action_line(text: str) -> Optional[dict]:
    """Parse an ACTION line emitted by the LLM."""
    for line in text.splitlines():
        if line.strip().startswith("ACTION:"):
            payload = line.split("ACTION:", 1)[1].strip()
            try:
                data = json.loads(payload)
                if isinstance(data, dict) and "action" in data and "params" in data:
                    return data
            except json.JSONDecodeError:
                continue
    return None


def _strip_action_lines(text: str) -> str:
    """Remove ACTION lines from assistant output before showing the user."""
    lines = [line for line in text.splitlines() if not line.strip().startswith("ACTION:")]
    return "\n".join(lines).strip()


def _format_datetime(value: Optional[object]) -> str:
    if value is None:
        return "N/A"
    return str(value)


def _format_action_result(action_name: str, action_result: object) -> str:
    if isinstance(action_result, dict) and action_result.get("error"):
        return f"Action failed: {action_result['error']}"

    if action_name == "check_balance":
        if not isinstance(action_result, dict):
            return ""
        balance = action_result.get("balance_lkr")
        if balance is None:
            return "Balance is unavailable for this account."
        return f"Your balance is LKR {balance}."

    if action_name == "get_connection_info":
        if not isinstance(action_result, dict):
            return ""
        return (
            "Connection details:\n"
            f"- Status: {action_result.get('status', 'N/A')}\n"
            f"- Valid until: {_format_datetime(action_result.get('connection_valid_until'))}\n"
            f"- Phone: {action_result.get('phone_e164', 'N/A')}\n"
            f"- Email: {action_result.get('email', 'N/A')}"
        )

    if action_name == "list_recent_actions":
        if not isinstance(action_result, list):
            return ""
        if not action_result:
            return "No recent account actions found."
        lines = [
            f"- {item.get('action_name', 'action')} | {item.get('status', 'unknown')} | {_format_datetime(item.get('created_at'))}"
            for item in action_result
        ]
        return "Recent account actions:\n" + "\n".join(lines)

    if action_name == "list_subscriptions":
        if not isinstance(action_result, list):
            return ""
        if not action_result:
            return "No subscriptions found on this account."
        lines = [
            f"- {item.get('name', 'Service')} ({item.get('code', 'N/A')}) | {item.get('status', 'unknown')} | Expires: {_format_datetime(item.get('expires_at'))}"
            for item in action_result
        ]
        return "Subscriptions:\n" + "\n".join(lines)

    if action_name == "list_tickets":
        if not isinstance(action_result, list):
            return ""
        if not action_result:
            return "No tickets found for this account."
        lines = [
            f"- {item.get('external_id', 'TICKET')} | {item.get('subject', 'Support request')} | {item.get('status', 'unknown')}"
            for item in action_result
        ]
        return "Tickets:\n" + "\n".join(lines)

    if action_name == "create_ticket":
        if not isinstance(action_result, dict):
            return ""
        ticket_id = action_result.get("ticket_id")
        if ticket_id:
            return f"Ticket created: {ticket_id}."
        return "Ticket created."

    if action_name == "activate_service":
        if not isinstance(action_result, dict):
            return ""
        code = action_result.get("service_code", "service")
        status = action_result.get("status", "activated")
        return f"{code} is {status}."

    if action_name == "deactivate_service":
        if not isinstance(action_result, dict):
            return ""
        code = action_result.get("service_code", "service")
        status = action_result.get("status", "cancelled")
        return f"{code} is {status}."

    return ""


_AGENTIC_PATTERNS = [
    re.compile(r"\b(balance|check balance|account balance)\b", re.IGNORECASE),
    re.compile(r"\b(create|open|raise|file)\b.*\bticket\b", re.IGNORECASE),
    re.compile(r"\b(activate|enable|start|subscribe|buy|add)\b.*\b(service|plan|package|subscription|pack|vas|sms|voice|bundle)\b", re.IGNORECASE),
    re.compile(r"\b(deactivate|disable|stop|cancel|remove)\b.*\b(service|plan|package|subscription|pack|vas|sms|voice|bundle)\b", re.IGNORECASE),
    re.compile(r"\b(list|show|view)\b.*\b(subscriptions?|tickets?|actions?|activity|history)\b", re.IGNORECASE),
    re.compile(r"\b(check|track)\b.*\b(ticket|subscription|status)\b", re.IGNORECASE),
    re.compile(r"\b(live agent|human agent|talk to (a )?agent|representative|customer care|call back|callback)\b", re.IGNORECASE),
    re.compile(r"\b(connection|account)\b.*\b(info|information|details|status|validity|expiry|expires)\b", re.IGNORECASE),
    re.compile(r"\b(recent|latest)\b.*\b(actions?|activity|requests|history)\b", re.IGNORECASE),
    re.compile(r"\bmy\b.*\b(account|number|plan|subscription|ticket|balance|actions|activity)\b", re.IGNORECASE),
]


def _detect_agentic_intent(text: str) -> bool:
    if not text:
        return False
    return any(pattern.search(text) for pattern in _AGENTIC_PATTERNS)


_PHONE_RE = re.compile(r"^\+?\d{9,15}$")


def _normalize_phone(phone: str) -> str:
    cleaned = re.sub(r"[\s\-()]", "", phone)
    if not _PHONE_RE.match(cleaned):
        raise ValueError("Invalid phone number format")
    if not cleaned.startswith("+"):
        cleaned = f"+{cleaned}"
    return cleaned


@app.post("/api/chat")
async def chat(request: ChatRequest, http_request: Request):
    """Chat with conversation context, optionally streaming."""
    try:
        pipe = get_pipeline()
        # Optional bearer session
        session = None
        auth_header = http_request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            session = auth_service.validate_session(token)
        needs_verification = (session is None) and _detect_agentic_intent(request.message)
        
        if request.stream:
            # Streaming response using proper async pattern
            async def generate() -> AsyncGenerator[str, None]:
                async_queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
                error_holder: list[Exception] = []
                session_status = "verified" if session else "unverified"
                
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
                                session_status=session_status,
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
            session_status = "verified" if session else "unverified"
            result = await asyncio.to_thread(
                pipe.chat,
                request.message,
                None,
                request.session_id,
                session_status,
            )
            # Attempt action parsing (only non-streaming)
            action_data = _parse_action_line(result.answer)
            action_result = None
            action_name = None
            params: dict = {}
            if action_data:
                action_name = action_data.get("action")
                params = action_data.get("params") or {}
                if not session:
                    action_result = {"error": "Verification required before performing actions."}
                    needs_verification = True
                else:
                    try:
                        user_email = params.get("email") or session.get("email")
                        user_phone = params.get("phone") or session.get("phone_e164")
                        if action_name == "create_ticket":
                            action_result = action_service.create_ticket(
                                actor_id=session["user_id"],
                                actor_role=session["role"],
                                user_email=user_email,
                                user_phone=user_phone,
                                subject=params.get("subject", "Support request"),
                                description=params.get("description", ""),
                                priority=params.get("priority", "normal"),
                                idempotency_key=params.get("idempotency_key"),
                            )
                        elif action_name == "get_connection_info":
                            action_result = action_service.get_connection_info(
                                user_id=session["user_id"],
                            )
                        elif action_name == "activate_service":
                            service_code = params.get("service_code")
                            if not service_code:
                                raise ValueError("service_code is required")
                            action_result = action_service.activate_service(
                                actor_id=session["user_id"],
                                actor_role=session["role"],
                                user_email=user_email,
                                user_phone=user_phone,
                                service_code=service_code,
                                idempotency_key=params.get("idempotency_key"),
                            )
                        elif action_name == "deactivate_service":
                            service_code = params.get("service_code")
                            if not service_code:
                                raise ValueError("service_code is required")
                            action_result = action_service.deactivate_service(
                                actor_id=session["user_id"],
                                actor_role=session["role"],
                                user_email=user_email,
                                user_phone=user_phone,
                                service_code=service_code,
                                idempotency_key=params.get("idempotency_key"),
                            )
                        elif action_name == "list_subscriptions":
                            action_result = action_service.list_subscriptions(
                                user_email=user_email,
                                user_phone=user_phone,
                            )
                        elif action_name == "list_tickets":
                            action_result = action_service.list_tickets(
                                user_email=user_email,
                                user_phone=user_phone,
                                external_id=params.get("ticket_id") or params.get("external_id"),
                            )
                        elif action_name == "list_recent_actions":
                            raw_limit = params.get("limit", 5)
                            try:
                                limit_val = int(raw_limit)
                            except (TypeError, ValueError):
                                limit_val = 5
                            limit_val = min(max(limit_val, 1), 20)
                            action_result = action_service.list_recent_actions_by_user_id(
                                user_id=session["user_id"],
                                limit=limit_val,
                            )
                        elif action_name == "check_balance":
                            action_result = action_service.get_balance(
                                user_id=session["user_id"]
                            )
                        else:
                            action_result = {"error": f"Unsupported action: {action_name}"}
                    except Exception as e:
                        action_result = {"error": str(e)}
            
            clean_answer = _strip_action_lines(result.answer)
            if session is None and not needs_verification:
                if re.search(r"\b(otp|verification|verify|one-time)\b", result.answer, re.IGNORECASE):
                    needs_verification = True
            action_summary = ""
            if action_data and action_name:
                action_summary = _format_action_result(action_name, action_result)
            if action_summary:
                clean_answer = f"{clean_answer}\n\n{action_summary}".strip() if clean_answer else action_summary
            elif action_data and not clean_answer:
                clean_answer = "Got it. Working on that now."
            response_payload = {
                "answer": clean_answer,
                "sources": [
                    {
                        "source": s.get("source", ""),
                        "content": s.get("text", s.get("content", "")),
                    }
                    for s in result.sources
                ],
                "session_id": request.session_id,
                "needs_verification": needs_verification,
                "agentic": bool(action_data) or needs_verification,
            }
            if action_data:
                response_payload["action"] = action_data
                response_payload["action_result"] = action_result
            
            return response_payload
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


@app.post("/api/auth/otp/start")
async def start_otp(request: OtpStartRequest):
    """Start email OTP verification."""
    try:
        result = auth_service.start_email_otp(request.email)

        # Send email (or log if email is disabled)
        email_client.send(
            to_email=request.email,
            subject="Your verification code",
            body=f"Your verification code is {result['code']}. It expires in {auth_service.OTP_EXPIRY_MINUTES} minutes.",
        )

        return {"success": True, "expires_at": result["expires_at"].isoformat()}
    except Exception as e:
        logger.error(f"OTP start error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/otp/phone/start")
async def start_phone_otp(request: PhoneOtpStartRequest):
    """Start OTP verification using a mobile number (OTP delivered via email)."""
    try:
        phone = _normalize_phone(request.phone)
        result = auth_service.start_phone_otp(phone)

        email_client.send(
            to_email=result["destination"],
            subject="Your verification code",
            body=(
                f"Your verification code is {result['code']}. "
                f"It expires in {auth_service.OTP_EXPIRY_MINUTES} minutes."
            ),
        )

        return {"success": True, "expires_at": result["expires_at"].isoformat()}
    except Exception as e:
        logger.error(f"Phone OTP start error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/otp/confirm", response_model=SessionResponse)
async def confirm_otp(request: OtpConfirmRequest):
    """Confirm OTP and return a session token."""
    try:
        result = auth_service.confirm_email_otp(request.email, request.code)
        return {
            "token": result["session_token"],
            "expires_at": result["session_expires_at"],
            "user": result["user"],
        }
    except Exception as e:
        logger.error(f"OTP confirm error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/otp/phone/confirm", response_model=SessionResponse)
async def confirm_phone_otp(request: PhoneOtpConfirmRequest):
    """Confirm phone OTP and return a session token."""
    try:
        phone = _normalize_phone(request.phone)
        result = auth_service.confirm_phone_otp(phone, request.code)
        return {
            "token": result["session_token"],
            "expires_at": result["session_expires_at"],
            "user": result["user"],
        }
    except Exception as e:
        logger.error(f"Phone OTP confirm error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ----------------------------- Admin API ------------------------------------
@app.post("/api/admin/login")
async def admin_login(payload: AdminLoginRequest):
    if payload.username != settings.admin.username or payload.password != settings.admin.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_admin_token(payload.username)
    resp = JSONResponse(
        {"ok": True, "expires_at": int(time.time() + settings.admin.cookie_ttl_hours * 3600)}
    )
    resp.set_cookie(
        key=settings.admin.cookie_name,
        value=token,
        httponly=True,
        secure=not settings.is_development,
        samesite="lax",
        max_age=settings.admin.cookie_ttl_hours * 3600,
    )
    return resp


@app.post("/api/admin/logout")
async def admin_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(settings.admin.cookie_name)
    return resp


@app.get("/api/admin/stats")
async def admin_stats(request: Request):
    require_admin(request)
    return {
        "counts": _admin_counts(),
        "latest_tickets": _fetch_table("tickets", limit=5, offset=0),
        "latest_actions": _fetch_table("actions", limit=5, offset=0),
        "latest_audit_logs": _fetch_table("audit_logs", limit=5, offset=0),
    }


@app.get("/api/admin/table/{name}")
async def admin_table(name: str, request: Request, limit: int = 50, offset: int = 0):
    require_admin(request)
    return {"rows": _fetch_table(name, limit=limit, offset=offset)}


@app.put("/api/admin/table/{name}/{row_id}")
async def admin_update(name: str, row_id: str, payload: AdminUpdateRequest, request: Request):
    require_admin(request)
    updated = _update_table(name, row_id, payload.data)
    return {"row": updated}



def _require_session(request: Request) -> dict:
    """Extract and validate bearer token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth_header.split(" ", 1)[1].strip()
    session = auth_service.validate_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return session


@app.post("/api/actions/create_ticket")
async def create_ticket(request: CreateTicketRequest, http_request: Request):
    """Create a support ticket for a verified user."""
    session = _require_session(http_request)
    try:
        user_email = request.email or session.get("email")
        user_phone = request.phone or session.get("phone_e164")
        result = action_service.create_ticket(
            actor_id=session["user_id"],
            actor_role=session["role"],
            user_email=user_email,
            user_phone=user_phone,
            subject=request.subject,
            description=request.description,
            priority=request.priority,
            idempotency_key=request.idempotency_key,
        )
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Create ticket error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/actions/activate_service")
async def activate_service(request: ServiceChangeRequest, http_request: Request):
    """Activate a service for a user."""
    session = _require_session(http_request)
    try:
        user_email = request.email or session.get("email")
        user_phone = request.phone or session.get("phone_e164")
        result = action_service.activate_service(
            actor_id=session["user_id"],
            actor_role=session["role"],
            user_email=user_email,
            user_phone=user_phone,
            service_code=request.service_code,
            idempotency_key=request.idempotency_key,
        )
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Activate service error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/actions/deactivate_service")
async def deactivate_service(request: ServiceChangeRequest, http_request: Request):
    """Deactivate a service for a user."""
    session = _require_session(http_request)
    try:
        user_email = request.email or session.get("email")
        user_phone = request.phone or session.get("phone_e164")
        result = action_service.deactivate_service(
            actor_id=session["user_id"],
            actor_role=session["role"],
            user_email=user_email,
            user_phone=user_phone,
            service_code=request.service_code,
            idempotency_key=request.idempotency_key,
        )
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Deactivate service error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/actions/subscriptions")
async def list_subscriptions(http_request: Request, email: Optional[EmailStr] = None, phone: Optional[str] = None):
    """List subscriptions for a verified user."""
    session = _require_session(http_request)
    try:
        user_email = email or session.get("email")
        user_phone = phone or session.get("phone_e164")
        items = action_service.list_subscriptions(user_email=user_email, user_phone=user_phone)
        return {"subscriptions": items}
    except Exception as e:
        logger.error(f"List subscriptions error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/actions/tickets")
async def list_tickets(
    http_request: Request,
    email: Optional[EmailStr] = None,
    phone: Optional[str] = None,
    ticket_id: Optional[str] = None,
):
    """List tickets for a verified user."""
    session = _require_session(http_request)
    try:
        user_email = email or session.get("email")
        user_phone = phone or session.get("phone_e164")
        items = action_service.list_tickets(
            user_email=user_email,
            user_phone=user_phone,
            external_id=ticket_id,
        )
        return {"tickets": items}
    except Exception as e:
        logger.error(f"List tickets error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/actions/balance")
async def get_balance(http_request: Request):
    """Get account balance for a verified user."""
    session = _require_session(http_request)
    try:
        result = action_service.get_balance(user_id=session["user_id"])
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Balance error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/actions/connection")
async def get_connection_info(http_request: Request):
    """Get connection info for a verified user."""
    session = _require_session(http_request)
    try:
        result = action_service.get_connection_info(user_id=session["user_id"])
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Connection info error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/actions/recent-actions")
async def list_recent_actions(http_request: Request, limit: int = 5):
    """List recent account actions for a verified user."""
    session = _require_session(http_request)
    capped_limit = min(max(limit, 1), 20)
    try:
        items = action_service.list_recent_actions_by_user_id(
            user_id=session["user_id"],
            limit=capped_limit,
        )
        return {"actions": items}
    except Exception as e:
        logger.error(f"Recent actions error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/agentic/quick-actions")
async def agentic_quick_actions(http_request: Request):
    """Return quick actions tailored to the verified user."""
    session = _require_session(http_request)
    try:
        active_subs = action_service.list_active_subscriptions_by_user_id(
            user_id=session["user_id"]
        )
        available_services = action_service.list_available_services_by_user_id(
            user_id=session["user_id"],
            limit=6,
        )

        quick_actions = [
            {"id": "check_balance", "label": "Check balance", "message": "Check my balance."},
            {"id": "connection_info", "label": "Connection info", "message": "Show my connection information."},
            {"id": "recent_actions", "label": "Recent activity", "message": "Show my recent account actions."},
            {"id": "list_subscriptions", "label": "View subscriptions", "message": "List my subscriptions."},
            {"id": "list_tickets", "label": "View tickets", "message": "Show my tickets."},
            {"id": "live_agent", "label": "Talk to live agent", "message": "I want to talk to a live agent."},
        ]

        max_quick_actions = 8
        dynamic_slots = max(0, max_quick_actions - len(quick_actions))
        activate_slots = 0
        deactivate_slots = 0
        if dynamic_slots:
            activate_slots = min(len(available_services), (dynamic_slots + 1) // 2)
            deactivate_slots = min(len(active_subs), dynamic_slots - activate_slots)

            remaining = dynamic_slots - (activate_slots + deactivate_slots)
            if remaining:
                if len(available_services) - activate_slots > len(active_subs) - deactivate_slots:
                    activate_slots += min(remaining, len(available_services) - activate_slots)
                else:
                    deactivate_slots += min(remaining, len(active_subs) - deactivate_slots)

        for service in available_services[:activate_slots]:
            quick_actions.append({
                "id": f"activate_{service['code']}",
                "label": f"Activate {service['name']}",
                "message": f"Please activate {service['code']} for my account.",
            })

        for sub in active_subs[:deactivate_slots]:
            quick_actions.append({
                "id": f"deactivate_{sub['code']}",
                "label": f"Deactivate {sub['name']}",
                "message": f"Please deactivate {sub['code']} for my account.",
            })

        return {
            "user": {
                "id": session.get("user_id"),
                "display_name": session.get("display_name"),
                "email": session.get("email"),
                "phone_e164": session.get("phone_e164"),
            },
            "quick_actions": quick_actions,
            "active_subscriptions": active_subs,
            "available_services": available_services,
        }
    except Exception as e:
        logger.error(f"Quick actions error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
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


