import { uiMsg } from '@/lib/ui-messages';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { email, phone, subject, description, priority = 'normal', idempotency_key } = body;
    const token = request.headers.get('authorization');

    if (!token) {
      return Response.json({ error: uiMsg('api.error.unauthorized') }, { status: 401 });
    }

    if (!subject || !description) {
      return Response.json(
        { error: uiMsg('api.validation.subject_description_required') },
        { status: 400 }
      );
    }

    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

    const resp = await fetch(`${backendUrl}/api/actions/create_ticket`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: token,
      },
      body: JSON.stringify({ email, phone, subject, description, priority, idempotency_key }),
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
    console.error('Create ticket error:', error);
    return Response.json(
      { error: uiMsg('api.error.internal') },
      { status: 500 }
    );
  }
}
