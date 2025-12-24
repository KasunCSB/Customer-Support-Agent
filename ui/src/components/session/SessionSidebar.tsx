/**
 * Session Sidebar Component
 *
 * Sidebar showing list of chat sessions with search and actions.
 */

'use client';

import { useState, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { Plus, Search, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { SessionListItem } from './SessionListItem';
import { SessionListSkeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import type { ChatSession } from '@/types/api';

interface SessionSidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  isLoading?: boolean;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onRenameSession?: (id: string, title: string) => void;
  onDeleteSession?: (id: string) => void;
  className?: string;
}

const SessionSidebar = ({
  sessions,
  activeSessionId,
  isLoading = false,
  onSelectSession,
  onNewSession,
  onRenameSession,
  onDeleteSession,
  className,
}: SessionSidebarProps) => {
  const [searchQuery, setSearchQuery] = useState('');

  // Filter sessions by search query
  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessions;

    const query = searchQuery.toLowerCase();
    return sessions.filter(
      (session) =>
        session.title.toLowerCase().includes(query) ||
        session.messages.some((m) => m.content.toLowerCase().includes(query))
    );
  }, [sessions, searchQuery]);

  // Group sessions by date
  const groupedSessions = useMemo(() => {
    const groups: { label: string; sessions: ChatSession[] }[] = [];
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const weekAgo = new Date(today);
    weekAgo.setDate(weekAgo.getDate() - 7);

    const monthAgo = new Date(today);
    monthAgo.setMonth(monthAgo.getMonth() - 1);

    const todaySessions: ChatSession[] = [];
    const yesterdaySessions: ChatSession[] = [];
    const weekSessions: ChatSession[] = [];
    const monthSessions: ChatSession[] = [];
    const olderSessions: ChatSession[] = [];

    filteredSessions.forEach((session) => {
      const date = new Date(session.updatedAt);
      date.setHours(0, 0, 0, 0);

      if (date >= today) {
        todaySessions.push(session);
      } else if (date >= yesterday) {
        yesterdaySessions.push(session);
      } else if (date >= weekAgo) {
        weekSessions.push(session);
      } else if (date >= monthAgo) {
        monthSessions.push(session);
      } else {
        olderSessions.push(session);
      }
    });

    if (todaySessions.length > 0) {
      groups.push({ label: 'Today', sessions: todaySessions });
    }
    if (yesterdaySessions.length > 0) {
      groups.push({ label: 'Yesterday', sessions: yesterdaySessions });
    }
    if (weekSessions.length > 0) {
      groups.push({ label: 'This Week', sessions: weekSessions });
    }
    if (monthSessions.length > 0) {
      groups.push({ label: 'This Month', sessions: monthSessions });
    }
    if (olderSessions.length > 0) {
      groups.push({ label: 'Older', sessions: olderSessions });
    }

    return groups;
  }, [filteredSessions]);

  return (
    <aside
      className={cn(
        'flex flex-col h-full',
        'bg-neutral-50 dark:bg-neutral-900',
        'border-r border-neutral-200 dark:border-neutral-800',
        className
      )}
    >
      {/* Header */}
      <div className="p-4 space-y-3">
        <Button
          variant="primary"
          fullWidth
          onClick={onNewSession}
          leftIcon={<Plus className="w-4 h-4" />}
        >
          New Chat
        </Button>

        <div className="relative">
          <Input
            type="search"
            placeholder="Search chats..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            leftElement={<Search className="w-4 h-4" />}
            className="text-sm"
          />
        </div>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {isLoading ? (
          <div className="space-y-1">
            {Array.from({ length: 5 }).map((_, i) => (
              <SessionListSkeleton key={i} />
            ))}
          </div>
        ) : filteredSessions.length === 0 ? (
          <EmptyState
            icon={<MessageSquare className="w-full h-full" />}
            title={searchQuery ? 'No results' : 'No chats yet'}
            description={
              searchQuery
                ? 'Try a different search term'
                : 'Start a new chat to get going'
            }
          />
        ) : (
          <div className="space-y-4">
            {groupedSessions.map((group) => (
              <div key={group.label}>
                <div className="px-3 py-1.5 text-xs font-medium text-neutral-500 dark:text-neutral-400">
                  {group.label}
                </div>
                <div className="space-y-0.5">
                  {group.sessions.map((session) => (
                    <SessionListItem
                      key={session.id}
                      title={session.title}
                      updatedAt={session.updatedAt}
                      messageCount={session.messages.length}
                      isActive={session.id === activeSessionId}
                      onClick={() => onSelectSession(session.id)}
                      onRename={
                        onRenameSession
                          ? (title) => onRenameSession(session.id, title)
                          : undefined
                      }
                      onDelete={
                        onDeleteSession
                          ? () => onDeleteSession(session.id)
                          : undefined
                      }
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
};

export { SessionSidebar };
