import React, { useState, useRef, useEffect } from 'react'
import { Send, Square, Paperclip } from 'lucide-react'

function ChatInput({ onSendMessage, isLoading, onStopGeneration }) {
  const [message, setMessage] = useState('')
  const textareaRef = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px'
    }
  }, [message])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (message.trim() && !isLoading) {
      onSendMessage(message.trim())
      setMessage('')
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="border-t border-hema-border-light dark:border-hema-border-dark bg-hema-bg-light dark:bg-hema-bg-dark">
      <div className="max-w-3xl mx-auto px-4 py-4">
        <form onSubmit={handleSubmit} className="relative">
          <div className="flex items-end gap-2 p-2 rounded-2xl border border-hema-border-light dark:border-hema-border-dark bg-hema-input-light dark:bg-hema-input-dark focus-within:border-hema-primary focus-within:ring-1 focus-within:ring-hema-primary transition-all">
            {/* Attachment button (placeholder for future) */}
            <button
            {/* Textarea */}
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about energy usage, get recommendations, or control devices..."
              rows={1}
              className="flex-1 resize-none bg-transparent border-none outline-none text-hema-text-light dark:text-hema-text-dark placeholder-hema-text-secondary-light dark:placeholder-hema-text-secondary-dark text-sm py-2 px-1 max-h-[200px] custom-scrollbar"
              disabled={isLoading}
            />

            {/* Send/Stop button */}
            {isLoading ? (
              <button
                type="button"
                onClick={onStopGeneration}
                className="p-2 rounded-lg bg-hema-text-secondary-light/20 dark:bg-hema-text-secondary-dark/20 hover:bg-hema-text-secondary-light/30 dark:hover:bg-hema-text-secondary-dark/30 transition-colors"
                aria-label="Stop generation"
              >
                <Square className="w-5 h-5 text-hema-text-light dark:text-hema-text-dark" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!message.trim()}
                className={`p-2 rounded-lg transition-all ${
                  message.trim()
                    ? 'bg-hema-primary hover:bg-hema-primary-dark text-white'
                    : 'bg-hema-text-secondary-light/20 dark:bg-hema-text-secondary-dark/20 text-hema-text-secondary-light dark:text-hema-text-secondary-dark cursor-not-allowed'
                }`}
                aria-label="Send message"
              >
                <Send className="w-5 h-5" />
              </button>
            )}
          </div>
        </form>

        {/* Disclaimer */}
        <p className="text-xs text-center text-hema-text-secondary-light dark:text-hema-text-secondary-dark mt-2">
          HEMA provides energy insights and recommendations. Always verify important decisions.
        </p>
      </div>
    </div>
  )
}

export default ChatInput
