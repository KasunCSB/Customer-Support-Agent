/**
 * Agentic Panel
 *
 * Displays verification inputs and quick actions for verified users.
 */

'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import type { QuickAction } from '@/types/api';

interface AgenticPanelProps {
  needsVerification: boolean;
  isVerified: boolean;
  otpStep?: 'phone' | 'code';
  phone: string;
  code: string;
  status?: string;
  onPhoneChange: (value: string) => void;
  onCodeChange: (value: string) => void;
  onStartOtp: () => void;
  onConfirmOtp: () => void;
  quickActions: QuickAction[];
  isLoadingActions?: boolean;
  onQuickAction: (action: QuickAction) => void;
}

const AgenticPanel = ({
  needsVerification,
  isVerified,
  otpStep = 'phone',
  phone,
  code,
  status,
  onPhoneChange,
  onCodeChange,
  onStartOtp,
  onConfirmOtp,
  quickActions,
  isLoadingActions = false,
  onQuickAction,
}: AgenticPanelProps) => {
  const shouldShowPanel = needsVerification || isVerified;
  const actionsRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const updateScrollState = useCallback(() => {
    const el = actionsRef.current;
    if (!el) return;
    const maxScrollLeft = el.scrollWidth - el.clientWidth;
    setCanScrollLeft(el.scrollLeft > 4);
    setCanScrollRight(el.scrollLeft < maxScrollLeft - 4);
  }, []);

  useEffect(() => {
    if (!shouldShowPanel) return;
    updateScrollState();
  }, [quickActions.length, isLoadingActions, shouldShowPanel, updateScrollState]);

  useEffect(() => {
    if (!shouldShowPanel) return;
    const handleResize = () => updateScrollState();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [shouldShowPanel, updateScrollState]);

  const scrollByAmount = (amount: number) => {
    actionsRef.current?.scrollBy({ left: amount, behavior: 'smooth' });
  };

  if (!shouldShowPanel) return null;

  return (
    <Card
      variant="flat"
      className="w-full max-w-[640px] bg-transparent border border-transparent shadow-none p-0"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="font-semibold text-neutral-900 dark:text-neutral-100">
          Account Actions
        </div>
        {isVerified && (
          <Badge variant="default" size="sm">
            Verified
          </Badge>
        )}
      </div>

      {!isVerified && needsVerification && (
        <div className="space-y-3">
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Account actions need verification. Enter your mobile number to receive a one-time code.
          </p>
          <div className="grid gap-3 md:grid-cols-[1fr_auto]">
            <Input
              value={phone}
              onChange={(e) => onPhoneChange(e.target.value)}
              placeholder="+94770011111"
              label="Mobile number"
            />
            <Button onClick={onStartOtp} variant="primary">
              {otpStep === 'code' ? 'Resend code' : 'Send code'}
            </Button>
          </div>
          {otpStep === 'code' && (
            <div className="grid gap-3 md:grid-cols-[1fr_auto]">
              <Input
                value={code}
                onChange={(e) => onCodeChange(e.target.value)}
                placeholder="6-digit code"
                label="Verification code"
              />
              <Button onClick={onConfirmOtp} variant="secondary">
                Verify
              </Button>
            </div>
          )}
          {status && (
            <div className="text-xs text-neutral-500 dark:text-neutral-400">
              {status}
            </div>
          )}
        </div>
      )}

      {isVerified && (
        <div className="space-y-2">
          <div className="text-sm text-neutral-600 dark:text-neutral-400">
            Quick actions for your account:
          </div>
          {isLoadingActions ? (
            <div className="text-xs text-neutral-500 dark:text-neutral-400">
              Loading actions...
            </div>
          ) : quickActions.length > 0 ? (
            <div className="relative">
              <div
                ref={actionsRef}
                onScroll={updateScrollState}
                className="flex gap-2 overflow-x-auto pb-1 flex-nowrap scrollbar-hide scroll-smooth"
              >
                {quickActions.map((action) => (
                  <Button
                    key={action.id}
                    variant="outline"
                    size="sm"
                    className="shrink-0 whitespace-nowrap"
                    onClick={() => onQuickAction(action)}
                  >
                    {action.label}
                  </Button>
                ))}
              </div>
              {canScrollLeft && (
                <button
                  type="button"
                  onClick={() => scrollByAmount(-240)}
                  className="absolute -left-3 top-1/2 -translate-y-1/2 rounded-full border border-white/40 dark:border-white/10 bg-white/90 dark:bg-neutral-900/90 text-neutral-700 dark:text-neutral-200 shadow-md backdrop-blur p-1.5"
                  aria-label="Scroll left"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
              )}
              {canScrollRight && (
                <button
                  type="button"
                  onClick={() => scrollByAmount(240)}
                  className="absolute -right-3 top-1/2 -translate-y-1/2 rounded-full border border-white/40 dark:border-white/10 bg-white/90 dark:bg-neutral-900/90 text-neutral-700 dark:text-neutral-200 shadow-md backdrop-blur p-1.5"
                  aria-label="Scroll right"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              )}
            </div>
          ) : (
            <div className="text-xs text-neutral-500 dark:text-neutral-400">
              No quick actions available yet.
            </div>
          )}
          {status && (
            <div className="text-xs text-neutral-500 dark:text-neutral-400">
              {status}
            </div>
          )}
        </div>
      )}
    </Card>
  );
};

export { AgenticPanel };
