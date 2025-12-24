/**
 * Modal Component
 *
 * A dialog modal with backdrop and animations.
 *
 * @example
 * ```tsx
 * <Modal isOpen={isOpen} onClose={handleClose} title="Confirm">
 *   Are you sure?
 * </Modal>
 * ```
 */

'use client';

import { Fragment, useEffect, useCallback, ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';
import { Button } from './Button';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  closeOnOverlayClick?: boolean;
  showCloseButton?: boolean;
  children: ReactNode;
  className?: string;
  footer?: ReactNode;
}

const Modal = ({
  isOpen,
  onClose,
  title,
  description,
  size = 'md',
  closeOnOverlayClick = true,
  showCloseButton = true,
  children,
  className,
  footer,
}: ModalProps) => {
  // Handle escape key
  const handleEscape = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, handleEscape]);

  if (!isOpen) return null;

  const sizes = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    full: 'max-w-4xl',
  };

  return (
    <Fragment>
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 z-50 bg-black/50 backdrop-blur-sm',
          'animate-fade-in'
        )}
        onClick={closeOnOverlayClick ? onClose : undefined}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        className={cn(
          'fixed inset-0 z-50 flex items-center justify-center p-4',
          'overflow-y-auto'
        )}
      >
        <div
          className={cn(
            'relative w-full rounded-2xl bg-white shadow-soft-lg',
            'dark:bg-neutral-900 dark:border dark:border-neutral-800',
            'animate-scale-in',
            sizes[size],
            className
          )}
          role="dialog"
          aria-modal="true"
          aria-labelledby={title ? 'modal-title' : undefined}
          aria-describedby={description ? 'modal-description' : undefined}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          {(title || showCloseButton) && (
            <div className="flex items-start justify-between p-6 pb-0">
              <div>
                {title && (
                  <h2
                    id="modal-title"
                    className="text-lg font-semibold text-neutral-900 dark:text-neutral-100"
                  >
                    {title}
                  </h2>
                )}
                {description && (
                  <p
                    id="modal-description"
                    className="mt-1 text-sm text-neutral-500 dark:text-neutral-400"
                  >
                    {description}
                  </p>
                )}
              </div>
              {showCloseButton && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onClose}
                  className="p-1.5 -mr-2 -mt-1"
                  aria-label="Close modal"
                >
                  <X className="h-5 w-5" />
                </Button>
              )}
            </div>
          )}

          {/* Content */}
          <div className="p-6">{children}</div>

          {/* Footer */}
          {footer && (
            <div className="flex items-center justify-end gap-3 px-6 pb-6 pt-2">
              {footer}
            </div>
          )}
        </div>
      </div>
    </Fragment>
  );
};

export { Modal };
