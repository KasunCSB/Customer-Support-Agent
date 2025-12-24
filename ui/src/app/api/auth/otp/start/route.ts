/**
 * OTP routes removed.
 */

export async function POST() {
  return Response.json(
    {
      error: 'Not found',
      message: 'Not found',
      code: 'NOT_FOUND',
    },
    { status: 404 }
  );
}
