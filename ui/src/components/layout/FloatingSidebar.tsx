/**
 * Floating Sidebar Component
 *
 * A modern floating sidebar with acrylic effect for chat history.
 * Slides in from the left with smooth animations.
 */

'use client';

import { useState, memo } from 'react';
import { cn } from '@/lib/utils';
import {
  PanelLeftClose,
  PanelLeftOpen,
  MessageSquare,
  Plus,
  Search,
  Trash2,
  Edit3,
  Check,
  X,
} from 'lucide-react';
import type { ChatSession } from '@/types/api';

interface FloatingSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession?: (id: string) => void;
  onRenameSession?: (id: string, title: string) => void;
  className?: string;
}

const FloatingSidebar = memo(function FloatingSidebar({
  isOpen,
  onToggle,
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onRenameSession,
  className,
}: FloatingSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  // Filter sessions
  const filteredSessions = sessions.filter((session) =>
    session.title.toLowerCase().includes(searchQuery.toLowerCase())
  );


  const handleStartEdit = (session: ChatSession) => {
    setEditingId(session.id);
    setEditTitle(session.title);
  };

  const handleSaveEdit = (id: string) => {
    if (editTitle.trim() && onRenameSession) {
      onRenameSession(id, editTitle.trim());
    }
    setEditingId(null);
    setEditTitle('');
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditTitle('');
  };

  return (
    <>
      {/* Toggle Button - Always visible */}
      <button
        onClick={onToggle}
        className={cn(
          'fixed left-4 top-20 z-50',
          'p-3 rounded-full',
          'bg-white/80 dark:bg-neutral-900/80',
          'backdrop-blur-xl',
          'border border-white/20 dark:border-white/10',
          'shadow-lg shadow-black/10 dark:shadow-black/30',
          'hover:bg-white dark:hover:bg-neutral-800',
          'hover:scale-105 active:scale-95',
          'transition-all duration-300'
        )}
        aria-label={isOpen ? 'Close sidebar' : 'Open sidebar'}
      >
        {isOpen ? (
          <PanelLeftClose className="w-5 h-5 text-neutral-700 dark:text-neutral-300" />
        ) : (
          <PanelLeftOpen className="w-5 h-5 text-neutral-700 dark:text-neutral-300" />
        )}
      </button>

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm lg:hidden"
          onClick={onToggle}
        />
      )}

      {/* Sidebar Panel */}
      <aside
        className={cn(
          'fixed left-4 top-32 bottom-4 z-40 w-80',
          'rounded-2xl overflow-hidden',
          'bg-white/80 dark:bg-neutral-900/80',
          'backdrop-blur-xl',
          'border border-white/20 dark:border-white/10',
          'shadow-2xl shadow-black/10 dark:shadow-black/40',
          'transition-all duration-300 ease-out',
          isOpen
            ? 'translate-x-0 opacity-100'
            : '-translate-x-[calc(100%+2rem)] opacity-0 pointer-events-none',
          className
        )}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-4 border-b border-neutral-200/50 dark:border-neutral-700/50">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-neutral-900 dark:text-white">
                Chat History
              </h2>
              <button
                onClick={onNewSession}
                className={cn(
                  'p-2 rounded-full',
                  'bg-primary-500/10 hover:bg-primary-500/20',
                  'text-primary-600 dark:text-primary-400',
                  'transition-colors duration-200'
                )}
                aria-label="New chat"
              >
                <Plus className="w-5 h-5" />
              </button>
            </div>

            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
              <input
                type="text"
                placeholder="Search conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={cn(
                  'w-full pl-10 pr-4 py-2 rounded-full',
                  'bg-neutral-100/50 dark:bg-neutral-800/50',
                  'border border-transparent',
                  'focus:border-primary-500/50 focus:ring-2 focus:ring-primary-500/20',
                  'text-sm text-neutral-900 dark:text-white',
                  'placeholder:text-neutral-400',
                  'transition-all duration-200'
                )}
              />
            </div>
          </div>

          {/* Session List */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {filteredSessions.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center p-4">
                <MessageSquare className="w-12 h-12 text-neutral-300 dark:text-neutral-600 mb-3" />
                <p className="text-sm text-neutral-500 dark:text-neutral-400">
                  {searchQuery
                    ? 'No matching conversations'
                    : 'No conversations yet'}
                </p>
                <button
                  onClick={onNewSession}
                  className="mt-3 text-sm text-primary-500 hover:text-primary-600"
                >
                  Start a new chat
                </button>
              </div>
            ) : (
              filteredSessions.map((session) => (
                <div
                  key={session.id}
                  className={cn(
                    'group relative flex items-center gap-3 p-3 rounded-xl',
                    'cursor-pointer transition-all duration-200',
                    activeSessionId === session.id
                      ? 'bg-primary-500/10 dark:bg-primary-500/20'
                      : 'hover:bg-neutral-100/50 dark:hover:bg-neutral-800/50'
                  )}
                  onClick={() => {
                    if (editingId !== session.id) {
                      onSelectSession(session.id);
                    }
                  }}
                >
                  <MessageSquare
                    className={cn(
                      'w-4 h-4 flex-shrink-0',
                      activeSessionId === session.id
                        ? 'text-primary-500'
                        : 'text-neutral-400'
                    )}
                  />

                  {editingId === session.id ? (
                    <div className="flex-1 flex items-center gap-2">
                      <input
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className={cn(
                          'flex-1 px-2 py-1 rounded-lg text-sm',
                          'bg-white dark:bg-neutral-800',
                          'border border-primary-500',
                          'focus:outline-none'
                        )}
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleSaveEdit(session.id);
                          if (e.key === 'Escape') handleCancelEdit();
                        }}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSaveEdit(session.id);
                        }}
                        className="p-1 rounded text-green-500 hover:bg-green-500/10"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCancelEdit();
                        }}
                        className="p-1 rounded text-red-500 hover:bg-red-500/10"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <>
                      <span
                        className={cn(
                          'flex-1 text-sm truncate',
                          activeSessionId === session.id
                            ? 'text-primary-700 dark:text-primary-300 font-medium'
                            : 'text-neutral-700 dark:text-neutral-300'
                        )}
                      >
                        {session.title}
                      </span>

                      {/* Action buttons */}
                      <div
                        className={cn(
                          'flex items-center gap-1 opacity-0 group-hover:opacity-100',
                          'transition-opacity duration-200'
                        )}
                      >
                        {onRenameSession && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleStartEdit(session);
                            }}
                            className="p-1 rounded text-neutral-400 hover:text-neutral-600 hover:bg-neutral-200/50 dark:hover:bg-neutral-700/50"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                        )}
                        {onDeleteSession && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onDeleteSession(session.id);
                            }}
                            className="p-1 rounded text-neutral-400 hover:text-red-500 hover:bg-red-500/10"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </aside>
    </>
  );
});

export { FloatingSidebar };
