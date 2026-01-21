import { uiMsg } from '@/lib/ui-messages';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { email, phone, service_code, idempotency_key } = body;
    const token = request.headers.get('authorization');

    if (!token) {
      return Response.json({ error: uiMsg('api.error.unauthorized') }, { status: 401 });
    }

    if (!service_code || typeof service_code !== 'string') {
      return Response.json(
        { error: uiMsg('api.validation.service_code_required') },
        { status: 400 }
      );
    }

    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

    const resp = await fetch(`${backendUrl}/api/actions/deactivate_service`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: token,
      },
      body: JSON.stringify({ email, phone, service_code, idempotency_key }),
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
    console.error('Deactivate service error:', error);
    return Response.json(
      { error: uiMsg('api.error.internal') },
      { status: 500 }
    );
  }
}
