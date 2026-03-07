// API service for communicating with the HEMA backend

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

/**
 * Handle API response and errors
 */
async function handleResponse(response) {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }
  return response.json()
}

/**
 * Chat API endpoints
 */
export const chatApi = {
  /**
   * Send a chat message and get a response
   * @param {string} message - User message
   * @param {string} sessionId - Session identifier
   * @param {AbortSignal} signal - Optional abort signal for cancellation
   * @returns {Promise<Object>} Chat response
   */
  async sendMessage(message, sessionId, signal) {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
      }),
      signal,
    })
    return handleResponse(response)
  },

  /**
   * Get chat history for a session
   * @param {string} sessionId - Session identifier
   * @returns {Promise<Object>} Session history
   */
  async getHistory(sessionId) {
    const response = await fetch(`${API_BASE_URL}/session/${sessionId}/history`)
    return handleResponse(response)
  },
}

/**
 * Session API endpoints
 */
export const sessionApi = {
  /**
   * Get session profile and status
   * @param {string} sessionId - Session identifier
   * @returns {Promise<Object>} Session profile
   */
  async getProfile(sessionId) {
    const response = await fetch(`${API_BASE_URL}/session/${sessionId}/profile`)
    return handleResponse(response)
  },

  /**
   * Delete/reset a session
   * @param {string} sessionId - Session identifier
   * @returns {Promise<Object>} Deletion result
   */
  async deleteSession(sessionId) {
    const response = await fetch(`${API_BASE_URL}/session/${sessionId}`, {
      method: 'DELETE',
    })
    return handleResponse(response)
  },
}

/**
 * Data API endpoints
 */
export const dataApi = {
  /**
   * List available data files
   * @returns {Promise<Object>} List of data files
   */
  async listFiles() {
    const response = await fetch(`${API_BASE_URL}/data/files`)
    return handleResponse(response)
  },

  /**
   * Upload an energy data file
   * @param {File} file - File to upload
   * @param {string} fileType - Type of file ('energy' or 'rate')
   * @returns {Promise<Object>} Upload result
   */
  async uploadFile(file, fileType = 'energy') {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('file_type', fileType)

    const response = await fetch(`${API_BASE_URL}/data/upload`, {
      method: 'POST',
      body: formData,
    })
    return handleResponse(response)
  },
}

/**
 * Health check endpoint
 */
export async function healthCheck() {
  const response = await fetch(`${API_BASE_URL}/health`)
  return handleResponse(response)
}

export default {
  chat: chatApi,
  session: sessionApi,
  data: dataApi,
  healthCheck,
}
