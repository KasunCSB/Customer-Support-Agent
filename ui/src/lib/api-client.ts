import type { AgenticContext, QueryResponse, SystemStats } from '@/types/api';

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.BACKEND_URL || 'http://localhost:8000';

export class APIClientError extends Error {
  code?: string;
  constructor(message: string, code?: string) {
    super(message);
    this.code = code;
  }
}

async function handleResponse(resp: Response) {
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new APIClientError(err.detail || err.error || `Request failed: ${resp.status}`);
  }
  return resp.json();
}

export const apiClient = {
  async chat(
    message: string,
    sessionId: string,
    opts?: { signal?: AbortSignal; authToken?: string }
  ) {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (opts?.authToken) {
      headers.Authorization = `Bearer ${opts.authToken}`;
    }
    const resp = await fetch(`${backendUrl}/api/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ message, session_id: sessionId, stream: false }),
      signal: opts?.signal,
    });
    return handleResponse(resp) as Promise<QueryResponse & { action?: unknown; action_result?: unknown; agentic?: boolean }>;
  },

  async startPhoneOtp(phone: string) {
    const resp = await fetch(`${backendUrl}/api/auth/otp/phone/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone }),
    });
    return handleResponse(resp) as Promise<{ success: boolean; expires_at?: string }>;
  },

  async confirmPhoneOtp(phone: string, code: string) {
    const resp = await fetch(`${backendUrl}/api/auth/otp/phone/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, code }),
    });
    return handleResponse(resp) as Promise<{ token: string; expires_at: string; user: unknown }>;
  },

  async getAgenticContext(opts?: { authToken?: string }) {
    const headers: Record<string, string> = {};
    if (opts?.authToken) {
      headers.Authorization = `Bearer ${opts.authToken}`;
    }
    const resp = await fetch(`${backendUrl}/api/agentic/quick-actions`, {
      method: 'GET',
      headers,
    });
    return handleResponse(resp) as Promise<AgenticContext>;
  },

  async getWelcomeMessage() {
    const resp = await fetch(`${backendUrl}/api/welcome`);
    return handleResponse(resp) as Promise<{ message: string }>;
  },

  async healthCheck() {
    const resp = await fetch(`${backendUrl}/api/health`);
    return handleResponse(resp) as Promise<{ status: string }>;
  },

  async getStats() {
    const resp = await fetch(`${backendUrl}/api/stats`);
    return handleResponse(resp) as Promise<SystemStats>;
  },
};
