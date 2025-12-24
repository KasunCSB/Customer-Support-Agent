/**
 * Memory Clear API Route
 *
 * Clear conversation memory in the backend.
 */
export const dynamic = 'force-dynamic';
export async function POST() {
  try {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

    const response = await fetch(`${backendUrl}/api/memory/clear`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return Response.json(
        { error: errorData.detail || 'Failed to clear memory' },
        { status: response.status }
      );
    }

    const data = await response.json();

    return Response.json({
      success: data.success ?? true,
      message: data.message ?? 'Memory cleared',
    });
  } catch (error) {
    console.error('Memory clear API error:', error);
    return Response.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
