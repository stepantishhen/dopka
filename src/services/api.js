const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

function getAuthHeaders() {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
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

  async listExams() {
    return this.request('/exams')
  }


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


  async createSession(studentId, examId = null) {
    return this.request('/orchestrator/sessions', {
      method: 'POST',
      body: { student_id: studentId, exam_id: examId },
    })
  }

  async getSession(sessionId) {
    return this.request(`/orchestrator/sessions/${sessionId}`)
  }

  async completeSession(sessionId) {
    return this.request(`/orchestrator/sessions/${sessionId}/complete`, {
      method: 'POST',
    })
  }

  async submitAnswer(sessionId, questionId, answer, questionData) {
    return this.request(`/orchestrator/sessions/${sessionId}/answer`, {
      method: 'POST',
      body: {
        session_id: sessionId,
        question_id: questionId,
        answer: answer,
        question_data: questionData,
      },
    })
  }

  async getNextQuestion(sessionId, examConfig) {
    return this.request(`/orchestrator/sessions/${sessionId}/next-question`, {
      method: 'POST',
      body: {
        session_id: sessionId,
        exam_config: examConfig,
      },
    })
  }

  async getInsights(sessionId, studentId) {
    return this.request(`/orchestrator/sessions/${sessionId}/insights`, {
      method: 'POST',
      body: {
        session_id: sessionId,
        student_id: studentId,
      },
    })
  }

  async getDialogueHistory(sessionId) {
    return this.request(`/orchestrator/sessions/${sessionId}/dialogue`)
  }

  async getMetrics() {
    return this.request('/metrics')
  }

  async getTeacherStudents() {
    return this.request('/teacher/students')
  }

  async getStudentAnalytics(studentId) {
    return this.request(`/teacher/students/${encodeURIComponent(studentId)}/analytics`)
  }


  async register(email, password, name, role = 'student') {
    return this.request('/auth/register', {
      method: 'POST',
      body: { email, password, name, role },
    })
  }

  async login(email, password) {
    return this.request('/auth/login', {
      method: 'POST',
      body: { email, password },
    })
  }

  async getExamByJoinCode(joinCode) {
    return this.request(`/exams/join/${encodeURIComponent(joinCode)}`)
  }

  async createSampleExam() {
    return this.request('/exams/create-sample', {
      method: 'POST',
    })
  }

  async createExamFromMaterials(name, text, unitIds = null, numQuestions = 10, adaptive = true) {
    return this.request('/exams/create-from-materials', {
      method: 'POST',
      body: {
        name,
        text,
        unit_ids: unitIds,
        num_questions: numQuestions,
        adaptive,
        questions_per_unit: 3,
      },
    })
  }

  async createExamFromPDF(file, name = null, numQuestions = 10, adaptive = true) {
    const formData = new FormData()
    formData.append('file', file)
    if (name) {
      formData.append('name', name)
    }
    formData.append('num_questions', numQuestions.toString())
    formData.append('adaptive', adaptive.toString())
    formData.append('questions_per_unit', '3')

    return this.request('/exams/create-from-pdf', {
      method: 'POST',
      headers: {},
      body: formData,
    })
  }
}

export default new ApiService()

