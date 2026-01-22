export type FriendlyError = {
  title: string;
  message: string;
};

export function getFriendlyError(err: unknown): FriendlyError {
  if (err instanceof Error) {
    return { title: 'Request failed', message: err.message };
  }
  return { title: 'Request failed', message: 'Something went wrong.' };
}
