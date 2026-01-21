/**
 * TTS API Route
 *
 * Proxy text-to-speech requests to backend Azure TTS service.
 */

import { uiMsg } from '@/lib/ui-messages';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { text, voice } = body;

    if (!text || typeof text !== 'string') {
      return Response.json(
        { error: uiMsg('api.validation.text_required') },
        { status: 400 }
      );
    }

    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

    const response = await fetch(`${backendUrl}/api/tts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text,
        voice,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return Response.json(
        { error: errorData.detail || uiMsg('api.error.tts_failed') },
        { status: response.status }
      );
    }

    // Stream the audio data back
    const audioData = await response.arrayBuffer();
    
    return new Response(audioData, {
      headers: {
        'Content-Type': 'audio/mpeg',
        'Content-Length': String(audioData.byteLength),
      },
    });
  } catch (error) {
    console.error('TTS API error:', error);
    return Response.json(
      { error: uiMsg('api.error.internal') },
      { status: 500 }
    );
  }
}
