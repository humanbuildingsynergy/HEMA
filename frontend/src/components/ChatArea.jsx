import { useRef, useEffect, useState } from 'react'
import { Zap, Sparkles, BarChart3, Lightbulb, Thermometer } from 'lucide-react'
import Message from './Message'
import ChatInput from './ChatInput'
import { chatApi } from '../services/api'

// Welcome screen suggestions
const SUGGESTIONS = [
  {
    icon: BarChart3,
    title: 'Analyze my energy usage',
    description: 'Load and analyze your energy consumption data',
    prompt: 'Can you load my energy data and analyze my consumption patterns?'
  },
  {
    icon: Lightbulb,
    title: 'Get energy tips',
    description: 'Learn about energy-saving best practices',
    prompt: 'What are the best practices for reducing my home energy consumption?'
  },
  {
    icon: Thermometer,
    title: 'Control thermostat',
    description: 'Manage your smart home devices',
    prompt: 'What is the current thermostat status and what temperature do you recommend?'
  },
  {
    icon: Sparkles,
    title: 'Explain TOU rates',
    description: 'Understand time-of-use pricing',
    prompt: 'Can you explain how time-of-use electricity rates work and how I can save money?'
  }
]

function ChatArea({
  sessionId,
  messages,
  onUpdateMessages,
}) {
  const messagesEndRef = useRef(null)
  const [isLoading, setIsLoading] = useState(false)
  const abortControllerRef = useRef(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSendMessage = async (content) => {
    if (!sessionId) return

    // Add user message
    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    }

    const updatedMessages = [...messages, userMessage]
    onUpdateMessages(updatedMessages)

    // Add streaming placeholder for assistant
    const assistantMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true
    }

    onUpdateMessages([...updatedMessages, assistantMessage])
    setIsLoading(true)

    try {
      abortControllerRef.current = new AbortController()

      const response = await chatApi.sendMessage(
        content,
        sessionId,
        abortControllerRef.current.signal
      )

      // Update with actual response
      const finalMessages = [
        ...updatedMessages,
        {
          ...assistantMessage,
          content: response.response,
          isStreaming: false
        }
      ]
      onUpdateMessages(finalMessages)
    } catch (error) {
      if (error.name === 'AbortError') {
        // User cancelled - keep partial response
        const currentMessages = [...updatedMessages, {
          ...assistantMessage,
          content: assistantMessage.content || 'Response cancelled.',
          isStreaming: false
        }]
        onUpdateMessages(currentMessages)
      } else {
        
        // Show error message
        const errorMessages = [
          ...updatedMessages,
          {
            ...assistantMessage,
            content: `I encountered an error: ${error.message}. Please try again.`,
            isStreaming: false
          }
        ]
        onUpdateMessages(errorMessages)
      }
    } finally {
      setIsLoading(false)
      abortControllerRef.current = null
    }
  }

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
  }

  const handleSuggestionClick = (prompt) => {
    handleSendMessage(prompt)
  }

  return (
    <div className="flex-1 flex flex-col min-w-0">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {messages.length === 0 ? (
          // Welcome screen
          <div className="h-full flex flex-col items-center justify-center px-4 py-8">
            <div className="max-w-2xl w-full">
              {/* Logo and title */}
              <div className="text-center mb-8">
                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-hema-primary to-hema-primary-dark flex items-center justify-center">
                  <Zap className="w-10 h-10 text-white" />
                </div>
                <h1 className="text-2xl font-semibold text-hema-text-light dark:text-hema-text-dark mb-2">
                  Welcome to HEMA
                </h1>
                <p className="text-hema-text-secondary-light dark:text-hema-text-secondary-dark">
                  Home Energy Management Assistant
                </p>
              </div>

              {/* Suggestions grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {SUGGESTIONS.map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => handleSuggestionClick(suggestion.prompt)}
                    className="p-4 rounded-xl border border-hema-border-light dark:border-hema-border-dark
                      bg-hema-bg-light dark:bg-hema-bg-dark
                      hover:bg-hema-hover-light dark:hover:bg-hema-hover-dark
                      hover:border-hema-primary/50
                      transition-all text-left group"
                  >
                    <div className="flex items-start gap-3">
                      <div className="p-2 rounded-lg bg-hema-primary/10 text-hema-primary group-hover:bg-hema-primary/20 transition-colors">
                        <suggestion.icon className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="font-medium text-sm text-hema-text-light dark:text-hema-text-dark mb-0.5">
                          {suggestion.title}
                        </h3>
                        <p className="text-xs text-hema-text-secondary-light dark:text-hema-text-secondary-dark">
                          {suggestion.description}
                        </p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          // Messages list
          <div className="pb-4">
            {messages.map((message) => (
              <Message key={message.id} message={message} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <ChatInput
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
        onStopGeneration={handleStopGeneration}
      />
    </div>
  )
}

export default ChatArea
