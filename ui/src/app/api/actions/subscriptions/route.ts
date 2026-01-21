import { uiMsg } from '@/lib/ui-messages';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  try {
    const token = request.headers.get('authorization');
    if (!token) {
      return Response.json({ error: uiMsg('api.error.unauthorized') }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const email = searchParams.get('email');
    const phone = searchParams.get('phone');

    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    const params = new URLSearchParams();
    if (email) params.append('email', email);
    if (phone) params.append('phone', phone);

    const resp = await fetch(`${backendUrl}/api/actions/subscriptions?${params.toString()}`, {
      headers: {
        Authorization: token,
      },
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
    console.error('List subscriptions error:', error);
    return Response.json(
      { error: uiMsg('api.error.internal') },
      { status: 500 }
    );
  }
}
