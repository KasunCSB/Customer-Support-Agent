/**
 * Stats API Route
 *
 * Get system statistics.
 */

// Mark as dynamic to prevent static generation at build time
export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

    const response = await fetch(`${backendUrl}/api/stats`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // Add cache control to prevent stale data
      cache: 'no-store',
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return Response.json(
        { error: errorData.detail || 'Failed to fetch stats' },
        { status: response.status }
      );
    }

    const data = await response.json();

    // Map backend response to frontend format
    // Backend returns: document_count, collection_name, chunk_size, environment
    return Response.json({
      vectorStore: {
        documentCount: data.document_count ?? 0,
        collectionName: data.collection_name ?? 'default',
        directory: data.directory ?? './vectorstore',
      },
      configuration: {
        chunkSize: data.chunk_size ?? 500,
        chunkOverlap: data.chunk_overlap ?? 200,
        retrievalTopK: data.retrieval_top_k ?? 5,
        llmTemperature: data.llm_temperature ?? 0.7,
        environment: data.environment ?? 'development',
      },
      health: {
        embeddings: true,
        chat: true,
        vectorStore: true,
        speech: false,
      },
    });
  } catch (error) {
    console.error('Stats API error:', error);
    return Response.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
