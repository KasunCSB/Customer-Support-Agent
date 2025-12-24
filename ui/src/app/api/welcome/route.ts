/**
 * Welcome API Route
 *
 * Returns a context-aware, randomly generated welcome message from the backend.
 */

import { NextResponse } from 'next/server';

const API_BASE_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// Fallback welcome messages if backend is unavailable
const FALLBACK_MESSAGES = [
  'Hi — how can I help?',
  'What can I do for you?',
  'Ask me anything.',
  "Let's get started.",
];

export async function GET() {
  try {
    // Try to get a generated welcome from the backend
    const response = await fetch(`${API_BASE_URL}/welcome`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // Short timeout for welcome message
      signal: AbortSignal.timeout(5000),
    });

    if (response.ok) {
      const data = await response.json();
      return NextResponse.json({ message: data.message });
    }
  } catch {
    // Silently fall through to fallback
    console.warn('Welcome endpoint unavailable, using fallback');
  }

  // Return a random fallback message
  const randomMessage = FALLBACK_MESSAGES[Math.floor(Math.random() * FALLBACK_MESSAGES.length)];
  return NextResponse.json({ message: randomMessage });
}
