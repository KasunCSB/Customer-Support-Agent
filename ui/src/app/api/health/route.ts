/**
 * Health Check API Route
 *
 * Check backend health status.
 */

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

    const response = await fetch(`${backendUrl}/api/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // Short timeout for health checks
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      return Response.json(
        { status: 'error', error: 'Backend unhealthy' },
        { status: 503 }
      );
    }

    const data = await response.json();
    return Response.json({
      status: data.status || 'healthy',
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Health check error:', error);
    return Response.json(
      { status: 'error', error: 'Backend unreachable' },
      { status: 503 }
    );
  }
}
