/**
 * Voice Error Boundary Component
 *
 * Specialized error boundary for voice features that provides
 * helpful recovery options specific to voice/speech errors.
 */

'use client';

import { Component, ReactNode, ErrorInfo } from 'react';
import { AlertTriangle, Mic, RefreshCw, Volume2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { uiMsg } from '@/lib/ui-messages';

interface VoiceErrorBoundaryProps {
  children: ReactNode;
  onReset?: () => void;
}

interface VoiceErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorType: 'microphone' | 'speech' | 'tts' | 'generic';
}

/**
 * Determine the type of voice error for targeted messaging
 */
function categorizeError(error: Error): 'microphone' | 'speech' | 'tts' | 'generic' {
  const message = error.message.toLowerCase();
  
  if (message.includes('microphone') || message.includes('permission') || message.includes('notallowed')) {
    return 'microphone';
  }
  if (message.includes('speech recognition') || message.includes('speechrecognition')) {
    return 'speech';
  }
  if (message.includes('tts') || message.includes('audio') || message.includes('playback')) {
    return 'tts';
  }
  return 'generic';
}

const ERROR_CONTENT = {
  microphone: {
    title: uiMsg('voice.error.microphone.title'),
    message: uiMsg('voice.error.microphone.message'),
    icon: Mic,
    actions: [
      { label: uiMsg('voice.action.check_permissions'), action: 'permissions' },
      { label: uiMsg('voice.action.try_again'), action: 'retry' },
    ],
  },
  speech: {
    title: uiMsg('voice.error.speech.title'),
    message: uiMsg('voice.error.speech.message'),
    icon: Mic,
    actions: [
      { label: uiMsg('voice.action.try_again'), action: 'retry' },
      { label: uiMsg('voice.action.use_text'), action: 'text' },
    ],
  },
  tts: {
    title: uiMsg('voice.error.tts.title'),
    message: uiMsg('voice.error.tts.message'),
    icon: Volume2,
    actions: [
      { label: uiMsg('voice.action.try_again'), action: 'retry' },
    ],
  },
  generic: {
    title: uiMsg('voice.error.generic.title'),
    message: uiMsg('voice.error.generic.message'),
    icon: AlertTriangle,
    actions: [
      { label: uiMsg('voice.action.try_again'), action: 'retry' },
      { label: uiMsg('voice.action.use_text'), action: 'text' },
    ],
  },
};

class VoiceErrorBoundary extends Component<VoiceErrorBoundaryProps, VoiceErrorBoundaryState> {
  constructor(props: VoiceErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorType: 'generic' };
  }

  static getDerivedStateFromError(error: Error): VoiceErrorBoundaryState {
    return {
      hasError: true,
      error,
      errorType: categorizeError(error),
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Voice error caught by boundary:', error, errorInfo);
  }

  handleAction = (action: string) => {
    switch (action) {
      case 'retry':
        this.setState({ hasError: false, error: null, errorType: 'generic' });
        this.props.onReset?.();
        break;
      case 'permissions':
        // Try to trigger permission prompt by requesting microphone
        navigator.mediaDevices?.getUserMedia({ audio: true })
          .then(() => {
            this.setState({ hasError: false, error: null, errorType: 'generic' });
            this.props.onReset?.();
          })
          .catch(() => {
            // Permission still denied - keep error state
          });
        break;
      case 'text':
        // Navigate to text chat
        window.location.href = '/';
        break;
    }
  };

  render() {
    if (this.state.hasError) {
      const content = ERROR_CONTENT[this.state.errorType];
      const IconComponent = content.icon;

      return (
        <div className="flex-1 flex items-center justify-center p-4">
          <Card className="max-w-md w-full p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-warning-100 dark:bg-warning-900/30 flex items-center justify-center">
              <IconComponent className="w-8 h-8 text-warning-600 dark:text-warning-400" />
            </div>
            <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
              {content.title}
            </h1>
            <p className="text-neutral-600 dark:text-neutral-400 mb-6">
              {content.message}
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              {content.actions.map((actionItem, index) => (
                <Button
                  key={actionItem.action}
                  variant={index === 0 ? 'primary' : 'outline'}
                  onClick={() => this.handleAction(actionItem.action)}
                  leftIcon={actionItem.action === 'retry' ? <RefreshCw className="w-4 h-4" /> : undefined}
                >
                  {actionItem.label}
                </Button>
              ))}
            </div>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

export { VoiceErrorBoundary };
