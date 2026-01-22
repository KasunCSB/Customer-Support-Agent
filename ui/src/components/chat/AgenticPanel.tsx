/**
 * Agentic Panel
 *
 * Displays verification inputs and quick actions for verified users.
 */

'use client';

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
  if (!shouldShowPanel) return null;

  return (
    <Card variant="outlined" className="border-primary-200/60 dark:border-primary-500/20 bg-primary-50/40 dark:bg-neutral-900/60">
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
            <div className="flex gap-2 overflow-x-auto pb-1 flex-nowrap">
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
