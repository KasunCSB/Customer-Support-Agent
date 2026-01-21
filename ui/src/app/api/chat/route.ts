/**
 * Chat API Route
 *
 * Handles chat requests with streaming support.
 */

import { uiMsg } from '@/lib/ui-messages';

// Don't use edge runtime for SSE streaming - it can cause issues
// export const runtime = 'edge';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { message, sessionId, settings, stream = true } = body;

    if (!message || typeof message !== 'string') {
      return Response.json(
        { error: uiMsg('api.validation.message_required') },
        { status: 400 }
      );
    }

    // Forward to backend
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

    const response = await fetch(`${backendUrl}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        stream,
        temperature: settings?.temperature,
        max_tokens: settings?.maxTokens,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return Response.json(
        { error: errorData.detail || uiMsg('api.error.backend_failed') },
        { status: response.status }
      );
    }

    // Check if streaming response
    const contentType = response.headers.get('content-type') || '';
    
    if (stream && contentType.includes('text/event-stream')) {
      // Stream the response directly
      const transformStream = new TransformStream();
      const writer = transformStream.writable.getWriter();
      const reader = response.body?.getReader();

      if (!reader) {
        return Response.json(
          { error: uiMsg('api.error.no_response_body') },
          { status: 500 }
        );
      }

      // Process stream in background
      (async () => {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            await writer.write(value);
          }
        } catch (error) {
          console.error('Stream processing error:', error);
        } finally {
          await writer.close();
        }
      })();

      return new Response(transformStream.readable, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache, no-transform',
          'Connection': 'keep-alive',
          'X-Accel-Buffering': 'no',
        },
      });
    } else {
      // Non-streaming JSON response
      const data = await response.json();
      return Response.json({
        answer: data.answer,
        sources: data.sources || [],
        sessionId: data.session_id || sessionId,
      });
    }
  } catch (error) {
    console.error('Chat API error:', error);
    return Response.json(
      { error: uiMsg('api.error.internal') },
      { status: 500 }
    );
  }
}
