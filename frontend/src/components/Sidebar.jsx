import React from 'react'
import {
  Plus,
  MessageSquare,
  Trash2,
  Sun,
  Moon,
  PanelLeftClose,
  PanelLeft,
  Zap
} from 'lucide-react'
import { formatTimestamp } from '../utils/helpers'

function Sidebar({
  isOpen,
  onToggle,
  sessions,
  currentSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  darkMode,
  onToggleDarkMode
}) {
  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 md:hidden"
          onClick={onToggle}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed md:relative z-30 h-full
          bg-bear-sidebar-light dark:bg-bear-sidebar-dark
          border-r border-bear-border-light dark:border-bear-border-dark
          transition-all duration-300 ease-in-out
          flex flex-col
          ${isOpen ? 'w-64 translate-x-0' : 'w-0 -translate-x-full md:w-0'}
        `}
      >
        <div className={`flex flex-col h-full ${isOpen ? 'opacity-100' : 'opacity-0'} transition-opacity duration-200`}>
          {/* Header */}
          <div className="p-3 border-b border-bear-border-light dark:border-bear-border-dark">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-bear-primary to-bear-primary-dark flex items-center justify-center">
                  <Zap className="w-5 h-5 text-white" />
                </div>
                <span className="font-semibold text-bear-text-light dark:text-bear-text-dark">
                  BEMA
                </span>
              </div>
              <button
                onClick={onToggle}
                className="p-1.5 rounded-lg hover:bg-bear-hover-light dark:hover:bg-bear-hover-dark transition-colors"
                aria-label="Close sidebar"
              >
                <PanelLeftClose className="w-5 h-5 text-bear-text-secondary-light dark:text-bear-text-secondary-dark" />
              </button>
            </div>

            {/* New Chat Button */}
            <button
              onClick={onNewSession}
              className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg
                border border-bear-border-light dark:border-bear-border-dark
                hover:bg-bear-hover-light dark:hover:bg-bear-hover-dark
                text-bear-text-light dark:text-bear-text-dark
                transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span className="text-sm">New Chat</span>
            </button>
          </div>

          {/* Sessions List */}
          <div className="flex-1 overflow-y-auto custom-scrollbar p-2">
            <div className="space-y-1">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`
                    group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer
                    transition-colors relative
                    ${currentSessionId === session.id
                      ? 'bg-bear-hover-light dark:bg-bear-hover-dark'
                      : 'hover:bg-bear-hover-light/50 dark:hover:bg-bear-hover-dark/50'
                    }
                  `}
                  onClick={() => onSelectSession(session.id)}
                >
                  <MessageSquare className="w-4 h-4 flex-shrink-0 text-bear-text-secondary-light dark:text-bear-text-secondary-dark" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-bear-text-light dark:text-bear-text-dark truncate">
                      {session.title}
                    </p>
                    <p className="text-xs text-bear-text-secondary-light dark:text-bear-text-secondary-dark">
                      {formatTimestamp(session.createdAt)}
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onDeleteSession(session.id)
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 transition-all"
                    aria-label="Delete session"
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="p-3 border-t border-bear-border-light dark:border-bear-border-dark">
            <button
              onClick={onToggleDarkMode}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg
                hover:bg-bear-hover-light dark:hover:bg-bear-hover-dark
                text-bear-text-secondary-light dark:text-bear-text-secondary-dark
                transition-colors"
            >
              {darkMode ? (
                <>
                  <Sun className="w-4 h-4" />
                  <span className="text-sm">Light Mode</span>
                </>
              ) : (
                <>
                  <Moon className="w-4 h-4" />
                  <span className="text-sm">Dark Mode</span>
                </>
              )}
            </button>
          </div>
        </div>
      </aside>

      {/* Toggle button when sidebar is closed */}
      {!isOpen && (
        <button
          onClick={onToggle}
          className="fixed top-3 left-3 z-10 p-2 rounded-lg
            bg-bear-bg-light dark:bg-bear-bg-dark
            border border-bear-border-light dark:border-bear-border-dark
            hover:bg-bear-hover-light dark:hover:bg-bear-hover-dark
            transition-colors"
          aria-label="Open sidebar"
        >
          <PanelLeft className="w-5 h-5 text-bear-text-secondary-light dark:text-bear-text-secondary-dark" />
        </button>
      )}
    </>
  )
}

export default Sidebar
