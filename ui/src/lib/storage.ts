import { v4 as uuidv4 } from 'uuid';
import type { Message, ChatSession } from '@/types/api';

const STORAGE_KEY = 'ltagent_sessions';

type StoredSession = ChatSession;

function nowIso() {
  return new Date().toISOString();
}

function loadAll(): Record<string, StoredSession> {
  if (typeof window === 'undefined') return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

function saveAll(data: Record<string, StoredSession>) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // ignore
  }
}

export async function getSession(id: string): Promise<StoredSession | null> {
  const all = loadAll();
  return all[id] || null;
}

export async function updateSession(id: string, partial: Partial<StoredSession>): Promise<void> {
  const all = loadAll();
  const current = all[id] || { id, messages: [] };
  all[id] = { ...current, ...partial, updatedAt: nowIso() } as StoredSession;
  saveAll(all);
}

export async function addMessage(sessionId: string, message: Partial<Message>): Promise<void> {
  const all = loadAll();
  const current =
    all[sessionId] ||
    ({
      id: sessionId,
      title: 'New session',
      createdAt: nowIso(),
      updatedAt: nowIso(),
      messages: [] as Message[],
    } as StoredSession);
  current.messages = [...current.messages, message as Message];
  current.updatedAt = nowIso();
  all[sessionId] = current;
  saveAll(all);
}

export async function listSessions(): Promise<StoredSession[]> {
  return Object.values(loadAll());
}

export async function deleteSession(id: string): Promise<void> {
  const all = loadAll();
  delete all[id];
  saveAll(all);
}

export async function getAllSessions(): Promise<StoredSession[]> {
  return listSessions();
}

export async function createSession(title?: string): Promise<StoredSession> {
  const id = uuidv4();
  const createdAt = nowIso();
  const session: StoredSession = {
    id,
    title: title || 'New session',
    createdAt,
    updatedAt: createdAt,
    messages: [],
    metadata: {},
  };
  const all = loadAll();
  all[id] = session;
  saveAll(all);
  return session;
}

export async function renameSession(id: string, title: string): Promise<StoredSession | null> {
  const all = loadAll();
  const current = all[id];
  if (!current) return null;
  const updated = { ...current, title, updatedAt: nowIso() };
  all[id] = updated;
  saveAll(all);
  return updated;
}
