import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'ltagent_session_token';
const listeners = new Set<(token: string | null) => void>();
let cachedToken: string | null | undefined = undefined;

const readToken = () => {
  if (cachedToken !== undefined) return cachedToken;
  if (typeof window === 'undefined') return null;
  cachedToken = localStorage.getItem(STORAGE_KEY);
  return cachedToken;
};

const writeToken = (value: string | null) => {
  if (typeof window !== 'undefined') {
    if (value) {
      localStorage.setItem(STORAGE_KEY, value);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }
  cachedToken = value;
  listeners.forEach((listener) => listener(value));
};

export function useAuthSession() {
  const [token, setToken] = useState<string | null>(() => readToken() ?? null);

  useEffect(() => {
    const handleUpdate = (value: string | null) => setToken(value);
    listeners.add(handleUpdate);

    const syncFromStorage = () => {
      if (typeof window === 'undefined') return;
      const stored = localStorage.getItem(STORAGE_KEY);
      cachedToken = stored;
      setToken(stored);
    };

    syncFromStorage();

    const onStorage = (event: StorageEvent) => {
      if (event.key !== STORAGE_KEY) return;
      cachedToken = event.newValue;
      setToken(event.newValue);
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('storage', onStorage);
    }

    return () => {
      listeners.delete(handleUpdate);
      if (typeof window !== 'undefined') {
        window.removeEventListener('storage', onStorage);
      }
    };
  }, []);

  const saveToken = useCallback((value: string | null) => {
    writeToken(value);
  }, []);

  return { token, setToken: saveToken };
}
