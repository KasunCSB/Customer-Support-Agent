export type ChatModeId = 'chat' | 'voice' | 'realtime';

export type ChatMode = {
  id: ChatModeId;
  label: string;
  description: string;
  icon: 'MessageSquare' | 'Mic' | 'Waves';
};

export const APP_CONFIG = {
  name: 'Rashmi',
  tagline: 'your LankaTel support assistant',
};

export const CHAT_MODES: ChatMode[] = [
  {
    id: 'chat',
    label: 'Chat',
    description: 'Type to chat with Rashmi in text mode.',
    icon: 'MessageSquare',
  },
  {
    id: 'voice',
    label: 'Voice',
    description: 'Push-to-talk voice chat with Rashmi.',
    icon: 'Mic',
  },
  {
    id: 'realtime',
    label: 'Realtime',
    description: 'Full-duplex realtime voice with barge-in.',
    icon: 'Waves',
  },
];
