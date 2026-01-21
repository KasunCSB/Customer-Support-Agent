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
  if (!needsVerification && !isVerified) return null;

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
            Verify your account to run actions. Enter your mobile number to receive a code.
          </p>
          <div className="grid gap-3 md:grid-cols-[1fr_auto]">
            <Input
              value={phone}
              onChange={(e) => onPhoneChange(e.target.value)}
              placeholder="+94770011111"
              label="Mobile number"
            />
            <Button onClick={onStartOtp} variant="primary">
              Send code
            </Button>
          </div>
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
          ) : (
            <div className="flex flex-wrap gap-2">
              {quickActions.map((action) => (
                <Button
                  key={action.id}
                  variant="outline"
                  size="sm"
                  onClick={() => onQuickAction(action)}
                >
                  {action.label}
                </Button>
              ))}
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
