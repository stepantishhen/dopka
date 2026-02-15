import React, { createContext, useContext, useState, useEffect } from 'react'
import api from '../services/api'

const ExamSessionContext = createContext()

export const useExamSession = () => {
  const context = useContext(ExamSessionContext)
  if (!context) {
    throw new Error('useExamSession must be used within ExamSessionProvider')
  }
  return context
}

export const ExamSessionProvider = ({ children }) => {
  const [currentSession, setCurrentSession] = useState(null)
  const [currentQuestion, setCurrentQuestion] = useState(null)
  const [dialogueHistory, setDialogueHistory] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [insights, setInsights] = useState(null)

  const createSession = async (studentId, examId = null) => {
    try {
      setIsLoading(true)
      setError(null)
      const session = await api.createSession(studentId, examId)
      setCurrentSession(session)
      return session
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const loadNextQuestion = async (examConfig) => {
    if (!currentSession) {
      throw new Error('No active session')
    }

    try {
      setIsLoading(true)
      setError(null)
      const response = await api.getNextQuestion(currentSession.session_id, examConfig)
      setCurrentQuestion(response.question)
      return response.question
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const submitAnswer = async (questionId, answer, questionData) => {
    if (!currentSession) {
      throw new Error('No active session')
    }

    try {
      setIsLoading(true)
      setError(null)
      const result = await api.submitAnswer(
        currentSession.session_id,
        questionId,
        answer,
        questionData
      )


      const userMessage = {
        sender: 'user',
        text: answer,
        timestamp: new Date().toISOString(),
        question_id: questionId,
      }

      const aiMessages = []
      
      if (result.clarification) {
        aiMessages.push({
          sender: 'ai',
          text: result.clarification,
          timestamp: new Date().toISOString(),
          tactic: result.tactic,
          type: 'clarification',
        })
      }

      if (result.feedback) {
        aiMessages.push({
          sender: 'ai',
          text: result.feedback,
          timestamp: new Date().toISOString(),
          type: 'feedback',
        })
      }

      if (result.error_analysis) {
        aiMessages.push({
          sender: 'ai',
          text: `Анализ ошибки: ${result.error_analysis.error_description}`,
          timestamp: new Date().toISOString(),
          type: 'error_analysis',
          error_analysis: result.error_analysis,
        })
      }

      setDialogueHistory(prev => [...prev, userMessage, ...aiMessages])


      await loadDialogueHistory()

      return result
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const loadDialogueHistory = async () => {
    if (!currentSession) return

    try {
      const response = await api.getDialogueHistory(currentSession.session_id)
      setDialogueHistory(response.dialogue_history || [])
    } catch (err) {
      console.error('Failed to load dialogue history:', err)
    }
  }

  const loadInsights = async () => {
    if (!currentSession) return

    try {
      setIsLoading(true)
      const response = await api.getInsights(
        currentSession.session_id,
        currentSession.student_id
      )
      setInsights(response)
      return response
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const endSession = () => {
    setCurrentSession(null)
    setCurrentQuestion(null)
    setDialogueHistory([])
    setInsights(null)
    setError(null)
  }

  useEffect(() => {
    if (currentSession) {
      loadDialogueHistory()
    }
  }, [currentSession?.session_id])

  const value = {
    currentSession,
    currentQuestion,
    dialogueHistory,
    isLoading,
    error,
    insights,
    createSession,
    loadNextQuestion,
    submitAnswer,
    loadDialogueHistory,
    loadInsights,
    endSession,
  }

  return <ExamSessionContext.Provider value={value}>{children}</ExamSessionContext.Provider>
}

