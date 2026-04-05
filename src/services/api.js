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
    const isFormData = options.body instanceof FormData
    // Для FormData нельзя задавать Content-Type вручную — нужен boundary от браузера
    const headers = {
      ...getAuthHeaders(),
      ...(options.headers || {}),
    }
    if (!isFormData) {
      headers['Content-Type'] = headers['Content-Type'] || 'application/json'
    }

    const config = {
      ...options,
      headers,
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

  async extractFromDOCX(file) {
    const formData = new FormData()
    formData.append('file', file)
    return this.request('/knowledge-base/extract-from-docx', {
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

  /** Завершить входной MCQ-тест; на бэкенде выставляется порядок вопросов (сначала слабые темы). */
  async completePretest(sessionId, choices) {
    return this.request(`/orchestrator/sessions/${sessionId}/pretest`, {
      method: 'POST',
      body: { choices },
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

  /** Тестовая среда: код экзамена, демо-логины (только при SEED_TEST_ENV / debug) */
  async getTestEnvironment() {
    return this.request('/dev/test-environment')
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

  async createExamFromDOCX(file, name = null, numQuestions = 10, adaptive = true) {
    const formData = new FormData()
    formData.append('file', file)
    if (name) {
      formData.append('name', name)
    }
    formData.append('num_questions', numQuestions.toString())
    formData.append('adaptive', adaptive.toString())
    formData.append('questions_per_unit', '3')
    return this.request('/exams/create-from-docx', {
      method: 'POST',
      headers: {},
      body: formData,
    })
  }

  async getTeacherMonitoringSessions() {
    return this.request('/teacher/monitoring/sessions')
  }

  async getTeacherAnalyticsByExam() {
    return this.request('/teacher/analytics/by-exam')
  }

  async exportAnalyticsJson() {
    return this.request('/teacher/export/analytics?format=json')
  }

  async downloadAnalyticsCsv() {
    const token = localStorage.getItem('token')
    const url = `${this.baseURL}/teacher/export/analytics?format=csv`
    const response = await fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(err.detail || `HTTP ${response.status}`)
    }
    const blob = await response.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `analytics_${new Date().toISOString().slice(0, 16).replace(/[:T]/, '_')}.csv`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  async importStudentsCsv(file) {
    const formData = new FormData()
    formData.append('file', file)
    return this.request('/teacher/students/import', {
      method: 'POST',
      headers: {},
      body: formData,
    })
  }
}

export default new ApiService()

