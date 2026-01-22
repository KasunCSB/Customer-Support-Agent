/**
 * API Types and Zod Schemas
 *
 * Defines all API request/response types with runtime validation using Zod.
 * These schemas match the backend Python dataclasses and API contracts.
 */

import { z } from 'zod';

// ============================================================================
// Chat Types
// ============================================================================

/**
 * Message role enum
 */
export const MessageRoleSchema = z.enum(['user', 'assistant', 'system']);
export type MessageRole = z.infer<typeof MessageRoleSchema>;

/**
 * Chat message schema
 */
export const MessageSchema = z.object({
  id: z.string().uuid(),
  role: MessageRoleSchema,
  content: z.string(),
  timestamp: z.string().datetime(),
  sources: z
    .array(
      z.object({
        source: z.string(),
        relevance: z.number().optional(),
      })
    )
    .optional(),
  tokens: z.number().optional(),
  model: z.string().optional(),
  isStreaming: z.boolean().optional(),
  error: z.string().optional(),
});
export type Message = z.infer<typeof MessageSchema>;

/**
 * Chat session schema
 */
export const ChatSessionSchema = z.object({
  id: z.string().uuid(),
  title: z.string(),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
  messages: z.array(MessageSchema),
  metadata: z
    .object({
      model: z.string().optional(),
      totalTokens: z.number().optional(),
      topK: z.number().optional(),
    })
    .optional(),
});
export type ChatSession = z.infer<typeof ChatSessionSchema>;

// ============================================================================
// API Request/Response Schemas
// ============================================================================

/**
 * Query request schema
 */
export const QueryRequestSchema = z.object({
  question: z.string().min(1, 'Question is required'),
  topK: z.number().int().min(1).max(20).optional().default(5),
  stream: z.boolean().optional().default(false),
  sessionId: z.string().uuid().optional(),
  includeHistory: z.boolean().optional().default(true),
});
export type QueryRequest = z.infer<typeof QueryRequestSchema>;

/**
 * Query response schema
 */
export const QueryResponseSchema = z.object({
  answer: z.string(),
  query: z.string().optional().nullable(),
  agentic: z.boolean().optional(),
  needs_verification: z.boolean().optional(),
  session_valid: z.boolean().optional().nullable(),
  sources: z.array(
    z.object({
      source: z.string(),
      content: z.string().optional().nullable(),
      relevance: z.number().optional().nullable(),
      score: z.number().optional().nullable(),
    })
  ).default([]),
  model: z.string().optional().nullable(),
  tokensUsed: z.object({
    promptTokens: z.number().optional().nullable(),
    completionTokens: z.number().optional().nullable(),
    totalTokens: z.number().optional().nullable(),
  }).optional().nullable(),
  confidence: z.number().optional().nullable(),
  timestamp: z.string().datetime().optional().nullable(),
});
export type QueryResponse = z.infer<typeof QueryResponseSchema>;

export const QuickActionSchema = z.object({
  id: z.string(),
  label: z.string(),
  message: z.string(),
});
export type QuickAction = z.infer<typeof QuickActionSchema>;

export const AgenticContextSchema = z.object({
  user: z.object({
    id: z.string().optional(),
    display_name: z.string().optional(),
    email: z.string().optional(),
    phone_local: z.string().optional(),
  }).optional(),
  quick_actions: z.array(QuickActionSchema).default([]),
  active_subscriptions: z.array(
    z.object({
      id: z.string().optional(),
      code: z.string().optional(),
      name: z.string().optional(),
      status: z.string().optional(),
      activated_at: z.string().optional().nullable(),
      expires_at: z.string().optional().nullable(),
    })
  ).optional(),
  available_services: z.array(
    z.object({
      id: z.string().optional(),
      code: z.string().optional(),
      name: z.string().optional(),
      category: z.string().optional(),
      price: z.number().optional(),
      currency: z.string().optional(),
      validity_days: z.number().optional(),
    })
  ).optional(),
});
export type AgenticContext = z.infer<typeof AgenticContextSchema>;

/**
 * Streaming chunk schema
 */
export const StreamChunkSchema = z.object({
  type: z.enum(['token', 'chunk', 'sources', 'done', 'error']),
  content: z.string().optional(),
  sources: z
    .array(
      z.object({
        source: z.string(),
      })
    )
    .optional(),
  error: z.string().optional(),
});
export type StreamChunk = z.infer<typeof StreamChunkSchema>;

// ============================================================================
// Statistics & System Types
// ============================================================================

/**
 * System statistics schema
 */
export const SystemStatsSchema = z.object({
  vectorStore: z.object({
    collectionName: z.string().default('default'),
    documentCount: z.number().default(0),
    directory: z.string().optional(),
  }),
  configuration: z.object({
    chunkSize: z.number().default(500),
    chunkOverlap: z.number().default(200),
    retrievalTopK: z.number().default(5),
    llmTemperature: z.number().default(0.7),
    environment: z.string().default('development'),
  }),
  health: z.object({
    embeddings: z.boolean().default(true),
    chat: z.boolean().default(true),
    vectorStore: z.boolean().default(true),
    speech: z.boolean().optional(),
  }).optional(),
});
export type SystemStats = z.infer<typeof SystemStatsSchema>;

/**
 * Test result schema
 */
export const TestResultSchema = z.object({
  name: z.string(),
  passed: z.boolean(),
  message: z.string().optional(),
  duration: z.number().optional(),
});
export type TestResult = z.infer<typeof TestResultSchema>;

export const TestResultsSchema = z.object({
  results: z.array(TestResultSchema),
  totalPassed: z.number(),
  totalFailed: z.number(),
  timestamp: z.string().datetime().optional(),
});
export type TestResults = z.infer<typeof TestResultsSchema>;

// ============================================================================
// Configuration Types
// ============================================================================

/**
 * LLM configuration schema
 */
export const LLMConfigSchema = z.object({
  temperature: z.number().min(0).max(2).default(0.7),
  maxTokens: z.number().int().min(1).max(4096).default(300),
  presencePenalty: z.number().min(-2).max(2).default(0.1),
  frequencyPenalty: z.number().min(-2).max(2).default(0.1),
});
export type LLMConfig = z.infer<typeof LLMConfigSchema>;

/**
 * Chunking configuration schema
 */
export const ChunkingConfigSchema = z.object({
  chunkSize: z.number().int().min(100).max(4000).default(1000),
  chunkOverlap: z.number().int().min(0).max(1000).default(200),
});
export type ChunkingConfig = z.infer<typeof ChunkingConfigSchema>;

/**
 * Retrieval configuration schema
 */
export const RetrievalConfigSchema = z.object({
  topK: z.number().int().min(1).max(20).default(3),
  contextTokenBudget: z.number().int().min(100).max(8000).default(2000),
});
export type RetrievalConfig = z.infer<typeof RetrievalConfigSchema>;

/**
 * Speech configuration schema
 */
export const SpeechConfigSchema = z.object({
  language: z.string().default('en-US'),
  voiceName: z.string().default('en-US-JennyNeural'),
  speechTimeout: z.number().min(1).max(60).default(10),
  silenceTimeout: z.number().min(0.5).max(10).default(1.5),
});
export type SpeechConfig = z.infer<typeof SpeechConfigSchema>;

/**
 * Full settings schema
 */
export const SettingsSchema = z.object({
  llm: LLMConfigSchema,
  chunking: ChunkingConfigSchema,
  retrieval: RetrievalConfigSchema,
  speech: SpeechConfigSchema.optional(),
  apiKeys: z.object({
    azureOpenAI: z.boolean(),
    azureSpeech: z.boolean(),
  }),
});
export type Settings = z.infer<typeof SettingsSchema>;

// ============================================================================
// Ingestion Types
// ============================================================================

/**
 * Ingestion request schema
 */
export const IngestRequestSchema = z.object({
  path: z.string().min(1),
  recursive: z.boolean().optional().default(true),
});
export type IngestRequest = z.infer<typeof IngestRequestSchema>;

/**
 * Ingestion result schema
 */
export const IngestResultSchema = z.object({
  documentsProcessed: z.number(),
  chunksCreated: z.number(),
  chunksIngested: z.number(),
  errors: z.array(z.string()),
  success: z.boolean(),
});
export type IngestResult = z.infer<typeof IngestResultSchema>;

// ============================================================================
// Voice Types
// ============================================================================

/**
 * Voice state enum
 */
export const VoiceStateSchema = z.enum(['idle', 'listening', 'thinking', 'speaking', 'working']);
export type VoiceState = z.infer<typeof VoiceStateSchema>;

/**
 * Voice transcript schema
 */
export const VoiceTranscriptSchema = z.object({
  id: z.string().uuid(),
  role: MessageRoleSchema,
  text: z.string(),
  timestamp: z.string().datetime(),
  isFinal: z.boolean(),
});
export type VoiceTranscript = z.infer<typeof VoiceTranscriptSchema>;

/**
 * Voice session schema
 */
export const VoiceSessionSchema = z.object({
  id: z.string().uuid(),
  state: VoiceStateSchema,
  transcripts: z.array(VoiceTranscriptSchema),
  startedAt: z.string().datetime(),
  endedAt: z.string().datetime().optional(),
  turnCount: z.number(),
  topics: z.array(z.string()),
});
export type VoiceSession = z.infer<typeof VoiceSessionSchema>;

// ============================================================================
// Error Types
// ============================================================================

/**
 * API error schema
 */
export const APIErrorSchema = z.object({
  error: z.string(),
  message: z.string(),
  code: z.string().optional(),
  details: z.unknown().optional(),
});
export type APIError = z.infer<typeof APIErrorSchema>;
