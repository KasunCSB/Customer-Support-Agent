/**
 * Error Boundary Component
 *
 * Catches React errors and displays a fallback UI.
 */

'use client';

import { Component, ReactNode, ErrorInfo } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { uiMsg } from '@/lib/ui-messages';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error to console (in production, send to error tracking service)
    console.error('Error caught by boundary:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-neutral-50 dark:bg-neutral-950">
          <Card className="max-w-md w-full p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-error-100 dark:bg-error-900 flex items-center justify-center">
              <AlertTriangle className="w-8 h-8 text-error-600 dark:text-error-400" />
            </div>
            <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
              {uiMsg('ui.error_boundary.title')}
            </h1>
            <p className="text-neutral-600 dark:text-neutral-400 mb-6">
              {uiMsg('ui.error_boundary.description')}
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button
                variant="outline"
                onClick={() => window.location.reload()}
                leftIcon={<RefreshCw className="w-4 h-4" />}
              >
                {uiMsg('ui.error_boundary.refresh')}
              </Button>
              <Button variant="primary" onClick={this.handleReset}>
                {uiMsg('ui.error_boundary.try_again')}
              </Button>
            </div>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

export { ErrorBoundary };
