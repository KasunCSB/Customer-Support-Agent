/**
 * Component prop types
 */

import { ReactNode, HTMLAttributes, ButtonHTMLAttributes, InputHTMLAttributes } from 'react';

// ============================================================================
// Base Component Types
// ============================================================================

export type Size = 'sm' | 'md' | 'lg' | 'xl';
export type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline' | 'accent';

export interface BaseProps {
  className?: string;
  children?: ReactNode;
}

// ============================================================================
// Button Types
// ============================================================================

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, BaseProps {
  variant?: Variant;
  size?: Size;
  isLoading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  fullWidth?: boolean;
  /** Makes the button pill-shaped (fully rounded) */
  pill?: boolean;
  /** Adds floating/glass effect with backdrop blur */
  floating?: boolean;
}

// ============================================================================
// Input Types
// ============================================================================

export interface InputProps extends InputHTMLAttributes<HTMLInputElement>, BaseProps {
  label?: string;
  error?: string;
  hint?: string;
  leftElement?: ReactNode;
  rightElement?: ReactNode;
}

export interface TextareaProps extends HTMLAttributes<HTMLTextAreaElement>, BaseProps {
  label?: string;
  error?: string;
  hint?: string;
  rows?: number;
  maxRows?: number;
  autoResize?: boolean;
}

// ============================================================================
// Card Types
// ============================================================================

export interface CardProps extends HTMLAttributes<HTMLDivElement>, BaseProps {
  variant?: 'elevated' | 'outlined' | 'flat';
  padding?: Size | 'none';
  hoverable?: boolean;
}

// ============================================================================
// Modal Types
// ============================================================================

export interface ModalProps extends BaseProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  size?: Size;
  closeOnOverlayClick?: boolean;
  showCloseButton?: boolean;
}

// ============================================================================
// Toast Types
// ============================================================================

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  duration?: number;
}

// ============================================================================
// Chat Component Types
// ============================================================================

export interface ChatInputProps extends BaseProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  isLoading?: boolean;
}

export interface ChatMessageProps extends BaseProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  isStreaming?: boolean;
  sources?: Array<{ source: string }>;
  onCopy?: () => void;
  onRegenerate?: () => void;
}

export interface ChatMessagesListProps extends BaseProps {
  messages: Array<{
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp?: string;
    isStreaming?: boolean;
    sources?: Array<{ source: string }>;
  }>;
  isLoading?: boolean;
}

// ============================================================================
// Session Types
// ============================================================================

export interface SessionListItemProps extends BaseProps {
  id: string;
  title: string;
  updatedAt: string;
  messageCount: number;
  isActive?: boolean;
  onClick: () => void;
  onRename?: (newTitle: string) => void;
  onDelete?: () => void;
}

// ============================================================================
// Voice Component Types
// ============================================================================

export type VoiceOrbState = 'idle' | 'listening' | 'thinking' | 'speaking';

export interface VoiceOrbProps extends BaseProps {
  state: VoiceOrbState;
  size?: Size;
  onClick?: () => void;
  disabled?: boolean;
}

export interface VoiceTranscriptProps extends BaseProps {
  role: 'user' | 'assistant';
  text: string;
  isFinal?: boolean;
}

// ============================================================================
// Settings Types
// ============================================================================

export interface SettingsSectionProps extends BaseProps {
  title: string;
  description?: string;
}

export interface SliderProps extends BaseProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
  formatValue?: (value: number) => string;
}

// ============================================================================
// Layout Types
// ============================================================================

export interface SidebarProps extends BaseProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export interface NavItemProps extends BaseProps {
  href: string;
  icon?: ReactNode;
  label: string;
  isActive?: boolean;
  badge?: string | number;
}
