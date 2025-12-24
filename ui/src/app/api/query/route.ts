/**
 * Query API Route
 *
 * Single-shot query without streaming.
 */

import { NextRequest } from 'next/server';
export const dynamic = 'force-dynamic';
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { query, settings } = body;

    if (!query || typeof query !== 'string') {
      return Response.json(
        { error: 'Query is required' },
        { status: 400 }
      );
    }

    // Forward to backend
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

    const response = await fetch(`${backendUrl}/api/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        top_k: settings?.topK || 5,
        score_threshold: settings?.scoreThreshold || 0.7,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return Response.json(
        { error: errorData.detail || 'Backend request failed' },
        { status: response.status }
      );
    }

    const data = await response.json();

    return Response.json({
      answer: data.answer,
      sources: data.sources || [],
      confidence: data.confidence,
    });
  } catch (error) {
    console.error('Query API error:', error);
    return Response.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
