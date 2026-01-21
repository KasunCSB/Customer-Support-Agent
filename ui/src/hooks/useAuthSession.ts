import { useEffect, useState } from 'react';

const STORAGE_KEY = 'ltagent_session_token';

export function useAuthSession() {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const stored = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
    if (stored) {
      setToken(stored);
    }
  }, []);

  const saveToken = (value: string | null) => {
    if (typeof window === 'undefined') return;
    if (value) {
      localStorage.setItem(STORAGE_KEY, value);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
    setToken(value);
  };

  return { token, setToken: saveToken };
}
