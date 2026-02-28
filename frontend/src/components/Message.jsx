import React from 'react'
import ReactMarkdown from 'react-markdown'
import { User, Zap, Copy, Check } from 'lucide-react'

function Message({ message }) {
  const [copied, setCopied] = React.useState(false)
  const isUser = message.role === 'user'

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={`group py-6 ${isUser ? '' : 'bg-bear-message-light dark:bg-bear-message-dark'}`}>
      <div className="max-w-3xl mx-auto px-4 md:px-6">
        <div className="flex gap-4">
          {/* Avatar */}
          <div className={`
            flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center
            ${isUser
              ? 'bg-bear-text-secondary-light/20 dark:bg-bear-text-secondary-dark/20'
              : 'bg-gradient-to-br from-bear-primary to-bear-primary-dark'
            }
          `}>
            {isUser ? (
              <User className="w-5 h-5 text-bear-text-secondary-light dark:text-bear-text-secondary-dark" />
            ) : (
              <Zap className="w-5 h-5 text-white" />
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-sm text-bear-text-light dark:text-bear-text-dark">
                {isUser ? 'You' : 'BEMA'}
              </span>
            </div>

            <div className="prose dark:prose-invert prose-sm max-w-none text-sm">
              {message.isStreaming ? (
                <div className="flex items-center gap-1">
                  <span className="text-bear-text-light dark:text-bear-text-dark">
                    {message.content}
                  </span>
                  <span className="typing-cursor" />
                </div>
              ) : (
                <ReactMarkdown
                  components={{
                    p: ({ children }) => (
                      <p className="mb-3 last:mb-0 text-bear-text-light dark:text-bear-text-dark">
                        {children}
                      </p>
                    ),
                    ul: ({ children }) => (
                      <ul className="list-disc list-inside mb-3 space-y-1">
                        {children}
                      </ul>
                    ),
                    ol: ({ children }) => (
                      <ol className="list-decimal list-inside mb-3 space-y-1">
                        {children}
                      </ol>
                    ),
                    li: ({ children }) => (
                      <li className="text-bear-text-light dark:text-bear-text-dark">
                        {children}
                      </li>
                    ),
                    code: ({ inline, children }) => (
                      inline ? (
                        <code className="px-1.5 py-0.5 rounded bg-bear-hover-light dark:bg-bear-hover-dark text-bear-primary font-mono text-sm">
                          {children}
                        </code>
                      ) : (
                        <code className="block p-3 rounded-lg bg-bear-sidebar-light dark:bg-bear-sidebar-dark font-mono text-sm overflow-x-auto">
                          {children}
                        </code>
                      )
                    ),
                    pre: ({ children }) => (
                      <pre className="mb-3 rounded-lg overflow-hidden">
                        {children}
                      </pre>
                    ),
                    h1: ({ children }) => (
                      <h1 className="text-xl font-bold mb-3 text-bear-text-light dark:text-bear-text-dark">
                        {children}
                      </h1>
                    ),
                    h2: ({ children }) => (
                      <h2 className="text-lg font-bold mb-2 text-bear-text-light dark:text-bear-text-dark">
                        {children}
                      </h2>
                    ),
                    h3: ({ children }) => (
                      <h3 className="text-base font-bold mb-2 text-bear-text-light dark:text-bear-text-dark">
                        {children}
                      </h3>
                    ),
                    strong: ({ children }) => (
                      <strong className="font-semibold">{children}</strong>
                    ),
                    a: ({ href, children }) => (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-bear-primary hover:underline"
                      >
                        {children}
                      </a>
                    ),
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              )}
            </div>

            {/* Actions */}
            {!isUser && !message.isStreaming && (
              <div className="flex items-center gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={handleCopy}
                  className="p-1.5 rounded-lg hover:bg-bear-hover-light dark:hover:bg-bear-hover-dark transition-colors"
                  aria-label="Copy message"
                >
                  {copied ? (
                    <Check className="w-4 h-4 text-bear-primary" />
                  ) : (
                    <Copy className="w-4 h-4 text-bear-text-secondary-light dark:text-bear-text-secondary-dark" />
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Message
