import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import { generateSessionId } from './utils/helpers'

function App() {
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode')
    // Default to light mode (false)
    return saved !== null ? JSON.parse(saved) : false
  })
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [sessions, setSessions] = useState([])
  const [currentSessionId, setCurrentSessionId] = useState(null)
  const [messages, setMessages] = useState([])

  // Apply dark mode class
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem('darkMode', JSON.stringify(darkMode))
  }, [darkMode])

  // Initialize first session
  useEffect(() => {
    if (sessions.length === 0) {
      createNewSession()
    }
  }, [])

  const createNewSession = () => {
    const newSessionId = generateSessionId()
    const newSession = {
      id: newSessionId,
      title: 'New Chat',
      createdAt: new Date().toISOString(),
      messages: []
    }
    setSessions(prev => [newSession, ...prev])
    setCurrentSessionId(newSessionId)
    setMessages([])
  }

  const selectSession = (sessionId) => {
    setCurrentSessionId(sessionId)
    const session = sessions.find(s => s.id === sessionId)
    setMessages(session?.messages || [])
  }

  const updateSessionMessages = (sessionId, newMessages) => {
    setSessions(prev => prev.map(session => {
      if (session.id === sessionId) {
        // Update title from first user message
        const firstUserMsg = newMessages.find(m => m.role === 'user')
        const title = firstUserMsg
          ? firstUserMsg.content.slice(0, 30) + (firstUserMsg.content.length > 30 ? '...' : '')
          : session.title
        return { ...session, messages: newMessages, title }
      }
      return session
    }))
    setMessages(newMessages)
  }

  const deleteSession = (sessionId) => {
    setSessions(prev => prev.filter(s => s.id !== sessionId))
    if (currentSessionId === sessionId) {
      const remaining = sessions.filter(s => s.id !== sessionId)
      if (remaining.length > 0) {
        selectSession(remaining[0].id)
      } else {
        createNewSession()
      }
    }
  }

  return (
    <div className={`flex h-screen bg-bear-bg-light dark:bg-bear-bg-dark transition-theme`}>
      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={selectSession}
        onNewSession={createNewSession}
        onDeleteSession={deleteSession}
        darkMode={darkMode}
        onToggleDarkMode={() => setDarkMode(!darkMode)}
      />

      {/* Main Chat Area */}
      <ChatArea
        sessionId={currentSessionId}
        messages={messages}
        onUpdateMessages={(msgs) => updateSessionMessages(currentSessionId, msgs)}
      />
    </div>
  )
}

export default App
