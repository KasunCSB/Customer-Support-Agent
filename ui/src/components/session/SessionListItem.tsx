/**
 * Session List Item Component
 *
 * Individual session item in the sidebar.
 */

'use client';

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { cn } from '@/lib/utils';
import { MoreHorizontal, Pencil, Trash2, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface SessionListItemProps {
  id: string;
  title: string;
  updatedAt: string;
  messageCount: number;
  isActive?: boolean;
  onClick: () => void;
  onRename?: (newTitle: string) => void;
  onDelete?: () => void;
  className?: string;
}

const SessionListItem = ({
  title,
  updatedAt,
  messageCount,
  isActive = false,
  onClick,
  onRename,
  onDelete,
  className,
}: Omit<SessionListItemProps, 'id'>) => {
  const [showMenu, setShowMenu] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(title);
  const inputRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Focus input when editing starts
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
    return undefined;
  }, [isEditing]);

  // Close menu on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowMenu(false);
      }
    };

    if (showMenu) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
    return undefined;
  }, [showMenu]);

  const handleRename = () => {
    if (editValue.trim() && editValue !== title) {
      onRename?.(editValue.trim());
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleRename();
    } else if (e.key === 'Escape') {
      setEditValue(title);
      setIsEditing(false);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return date.toLocaleDateString([], { weekday: 'short' });
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };

  return (
    <div
      className={cn(
        'group relative rounded-lg transition-colors duration-150',
        isActive
          ? 'bg-primary-50 dark:bg-primary-950'
          : 'hover:bg-neutral-100 dark:hover:bg-neutral-800',
        className
      )}
    >
      <button
        onClick={onClick}
        className="w-full text-left p-3 pr-10"
        aria-current={isActive ? 'page' : undefined}
      >
        <div className="flex items-start gap-2">
          <MessageSquare
            className={cn(
              'w-4 h-4 mt-0.5 flex-shrink-0',
              isActive
                ? 'text-primary-600 dark:text-primary-400'
                : 'text-neutral-400'
            )}
          />
          <div className="flex-1 min-w-0">
            {isEditing ? (
              <input
                ref={inputRef}
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onBlur={handleRename}
                onKeyDown={handleKeyDown}
                className={cn(
                  'w-full px-1 py-0.5 -ml-1',
                  'bg-white dark:bg-neutral-900',
                  'border border-primary-500 rounded',
                  'text-sm font-medium',
                  'focus:outline-none focus:ring-2 focus:ring-primary-500'
                )}
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <div
                className={cn(
                  'text-sm font-medium truncate',
                  isActive
                    ? 'text-primary-900 dark:text-primary-100'
                    : 'text-neutral-900 dark:text-neutral-100'
                )}
              >
                {title}
              </div>
            )}
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xs text-neutral-500 dark:text-neutral-400">
                {formatDate(updatedAt)}
              </span>
              <span className="text-xs text-neutral-400 dark:text-neutral-500">
                · {messageCount} message{messageCount !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
        </div>
      </button>

      {/* Menu button */}
      <div className="absolute right-2 top-1/2 -translate-y-1/2" ref={menuRef}>
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            setShowMenu(!showMenu);
          }}
          className={cn(
            'p-1 h-auto opacity-0 group-hover:opacity-100 transition-opacity',
            showMenu && 'opacity-100'
          )}
          aria-label="Session options"
        >
          <MoreHorizontal className="w-4 h-4" />
        </Button>

        {/* Dropdown menu */}
        {showMenu && (
          <div
            className={cn(
              'absolute right-0 top-full mt-1 z-50',
              'w-36 py-1 rounded-lg shadow-soft-lg',
              'bg-white dark:bg-neutral-800',
              'border border-neutral-200 dark:border-neutral-700',
              'animate-scale-in origin-top-right'
            )}
          >
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowMenu(false);
                setIsEditing(true);
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700"
            >
              <Pencil className="w-4 h-4" />
              Rename
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowMenu(false);
                onDelete?.();
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-error-600 dark:text-error-400 hover:bg-error-50 dark:hover:bg-error-950"
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export { SessionListItem };
