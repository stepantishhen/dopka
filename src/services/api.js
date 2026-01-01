const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
      config.body = JSON.stringify(config.body)
    }

    try {
      const response = await fetch(url, config)
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(error.detail || `HTTP error! status: ${response.status}`)
      }
      return await response.json()
    } catch (error) {
      console.error('API request failed:', error)
      throw error
    }
  }

  // Knowledge Base API
  async getKnowledgeItems(search = null) {
    const params = search ? `?search=${encodeURIComponent(search)}` : ''
    return this.request(`/knowledge-base/items${params}`)
  }

  async createKnowledgeItem(item) {
    return this.request('/knowledge-base/items', {
      method: 'POST',
      body: item,
    })
  }

  async updateKnowledgeItem(id, updates) {
    return this.request(`/knowledge-base/items/${id}`, {
      method: 'PUT',
      body: updates,
    })
  }

  async deleteKnowledgeItem(id) {
    return this.request(`/knowledge-base/items/${id}`, {
      method: 'DELETE',
    })
  }

  async extractFromText(text) {
    return this.request('/knowledge-base/extract-from-text', {
      method: 'POST',
      body: { text },
    })
  }

  async extractFromPDF(file) {
    const formData = new FormData()
    formData.append('file', file)
    return this.request('/knowledge-base/extract-from-pdf', {
      method: 'POST',
      headers: {},
      body: formData,
    })
  }

  // Chat API
  async createChat(title = null) {
    return this.request('/chat', {
      method: 'POST',
      body: { title },
    })
  }

  async getChat(chatId) {
    return this.request(`/chat/${chatId}`)
  }

  async sendMessage(chatId, message) {
    return this.request(`/chat/${chatId}/message`, {
      method: 'POST',
      body: { message },
    })
  }

  async listChats() {
    return this.request('/chat')
  }

  // Exams API
  async createExam(examData) {
    return this.request('/exams', {
      method: 'POST',
      body: examData,
    })
  }

  async getCurrentExam() {
    return this.request('/exams/current')
  }

  async getExam(examId) {
    return this.request(`/exams/${examId}`)
  }

  async submitExam(examId, studentId, answers) {
    return this.request(`/exams/${examId}/submit`, {
      method: 'POST',
      body: {
        student_id: studentId,
        answers: answers.map(ans => ({
          question_id: ans.questionId || ans.question_id,
          answer: ans.answer,
        })),
      },
    })
  }

  // Students API
  async createStudent(name, group = null) {
    return this.request('/students', {
      method: 'POST',
      body: { name, group },
    })
  }

  async getStudentProfile(studentId) {
    return this.request(`/students/${studentId}`)
  }

  async assessEmotionalState(studentId, responses) {
    return this.request(`/students/${studentId}/emotional-state`, {
      method: 'POST',
      body: { student_id: studentId, responses },
    })
  }

  async diagnoseKnowledgeGaps(studentId, quickMode = true) {
    return this.request(`/students/${studentId}/diagnostic`, {
      method: 'POST',
      body: { student_id: studentId, quick_mode: quickMode },
    })
  }
}

export default new ApiService()

