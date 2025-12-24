/**
 * Test API Route
 *
 * Run system tests.
 */

export const dynamic = 'force-dynamic';

export async function POST() {
  try {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

    const response = await fetch(`${backendUrl}/api/test`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return Response.json(
        { error: errorData.detail || 'Failed to run tests' },
        { status: response.status }
      );
    }

    const data = await response.json();

    // Normalize results format from backend
    // Backend returns: { results: [{ name, passed, message?, duration? }] }
    const results = (data.results || []).map((r: Record<string, unknown>) => ({
      name: r.name || 'Unknown',
      passed: r.passed ?? false,
      message: r.message || null,
      duration: r.duration || null,
    }));

    const totalPassed = results.filter((r: { passed: boolean }) => r.passed).length;
    const totalFailed = results.filter((r: { passed: boolean }) => !r.passed).length;

    return Response.json({
      results,
      totalPassed,
      totalFailed,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Test API error:', error);
    return Response.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
