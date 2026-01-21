import { uiMsg } from '@/lib/ui-messages';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { email, code } = body;

    if (!email || typeof email !== 'string' || !code || typeof code !== 'string') {
      return Response.json(
        { error: uiMsg('api.validation.email_code_required') },
        { status: 400 }
      );
    }

    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

    const resp = await fetch(`${backendUrl}/api/auth/otp/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, code }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      return Response.json(
        { error: err.detail || uiMsg('api.error.backend_failed') },
        { status: resp.status }
      );
    }

    const data = await resp.json();
    return Response.json(data);
  } catch (error) {
    console.error('OTP confirm error:', error);
    return Response.json(
      { error: uiMsg('api.error.internal') },
      { status: 500 }
    );
  }
}
