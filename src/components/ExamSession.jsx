import React, { useState, useEffect } from 'react'
import { Container, Row, Col, Card, Form, Button, Alert, Badge, Spinner } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import { useExamSession } from '../context/ExamSessionContext'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

const ExamSession = ({ examId }) => {
  const navigate = useNavigate()
  const { user } = useAuth()
  const {
    currentSession,
    currentQuestion,
    dialogueHistory,
    isLoading,
    error,
    createSession,
    loadNextQuestion,
    submitAnswer,
    loadInsights,
  } = useExamSession()

  const [answer, setAnswer] = useState('')
  const [evaluation, setEvaluation] = useState(null)
  const [showInsights, setShowInsights] = useState(false)
  const [exam, setExam] = useState(null)
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [examLoading, setExamLoading] = useState(true)

  useEffect(() => {

    if (examId) {
      loadExam()
    } else {

      if (!currentSession && user) {
        setExamLoading(false)
        createSession(user.id || `student_${Date.now()}`, null)
          .then(() => {

            const defaultConfig = {
              num_questions: 10,
              adaptive: true,
              unit_ids: null,
            }
            loadNextQuestion(defaultConfig)
          })
          .catch(console.error)
      } else if (!user) {
        setExamLoading(false)
      }
    }

  }, [examId, user])

  const loadExam = async () => {
    if (!examId) {
      setExamLoading(false)
      return
    }

    try {
      setExamLoading(true)
      const examData = await api.getExam(examId)
      
      if (!examData) {
        throw new Error('Экзамен не найден')
      }

      setExam(examData)


      if (!currentSession && user) {
        try {
          const session = await createSession(
            user.id || `student_${Date.now()}`,
            examId
          )


          if (examData.questions && examData.questions.length > 0) {
            setCurrentQuestionIndex(0)
            setExamLoading(false)
          } else {

            const examConfig = {
              num_questions: examData.config?.num_questions || 10,
              adaptive: examData.config?.adaptive !== false,
              unit_ids: examData.config?.unit_ids || null,
            }
            await loadNextQuestion(examConfig)
            setExamLoading(false)
          }
        } catch (sessionErr) {
          console.error('Failed to create session:', sessionErr)
          setExamLoading(false)
        }
      } else {

        if (examData.questions && examData.questions.length > 0) {
          setCurrentQuestionIndex(0)
        }
        setExamLoading(false)
      }
    } catch (err) {
      console.error('Failed to load exam:', err)
      setExamLoading(false)
      alert(`Ошибка загрузки экзамена: ${err.message || 'Неизвестная ошибка'}`)

    }
  }


  const handleSubmitAnswer = async (e) => {
    e.preventDefault()
    const questionToAnswer = currentQuestion || (exam?.questions?.[currentQuestionIndex])
    if (!answer.trim() || !questionToAnswer) return

    const questionId = questionToAnswer.question_id || questionToAnswer.id || `q_${currentQuestionIndex || 0}`
    
    try {
      const result = await submitAnswer(
        questionId,
        answer,
        {
          question: questionToAnswer.question,
          reference_answer: questionToAnswer.reference_answer || '',
          criteria: questionToAnswer.criteria || [],
        }
      )

      setEvaluation(result)




      if (result.is_correct) {
        setTimeout(() => {
          moveToNextQuestion()
        }, 2000)
      }
    } catch (err) {
      console.error('Failed to submit answer:', err)
      alert(`Ошибка при отправке ответа: ${err.message}`)
    }
  }

  const moveToNextQuestion = () => {
    if (exam && exam.questions) {

      const nextIndex = currentQuestionIndex + 1
      if (nextIndex < exam.questions.length) {
        setCurrentQuestionIndex(nextIndex)
        setEvaluation(null)
        setAnswer('')
      } else {

        alert('Экзамен завершен! Все вопросы пройдены.')
        navigate('/')
      }
    } else {

      if (exam) {
        const examConfig = {
          num_questions: exam.config.num_questions,
          adaptive: exam.config.adaptive,
          unit_ids: exam.config.unit_ids,
        }
        loadNextQuestion(examConfig)
          .then(() => {
            setEvaluation(null)
            setAnswer('')
          })
          .catch(console.error)
      }
    }
  }

  const handleNextQuestion = () => {
    moveToNextQuestion()
  }

  const handleShowInsights = async () => {
    await loadInsights()
    setShowInsights(true)
  }


  const questionToDisplay = currentQuestion || (exam?.questions?.[currentQuestionIndex])


  if (examLoading || (examId && !exam && !error)) {
    return (
      <Container className="py-4">
        <div className="text-center">
          <Spinner animation="border" />
          <p className="mt-3">
            {examLoading ? 'Загрузка экзамена...' : 'Инициализация сессии...'}
          </p>
        </div>
      </Container>
    )
  }


  if (exam && !currentSession && !user) {
    return (
      <Container className="py-4">
        <Alert variant="warning">
          Необходимо войти в систему для прохождения экзамена
        </Alert>
      </Container>
    )
  }


  if (exam && (!exam.questions || exam.questions.length === 0) && !questionToDisplay && !isLoading) {
    return (
      <Container className="py-4">
        <Alert variant="info">
          В этом экзамене пока нет вопросов. Система генерирует вопросы...
        </Alert>
        {isLoading && (
          <div className="text-center mt-3">
            <Spinner animation="border" />
          </div>
        )}
      </Container>
    )
  }


  if (!examId && !currentSession && user) {
    return (
      <Container className="py-4">
        <div className="text-center">
          <Spinner animation="border" />
          <p className="mt-3">Инициализация сессии...</p>
        </div>
      </Container>
    )
  }

  return (
    <Container fluid className="py-4">
      <Row>
        <Col md={8}>
          <Card className="mb-4">
            <Card.Header className="d-flex justify-content-between align-items-center">
              <h5 className="mb-0">
                {exam ? exam.config.name : 'Экзамен'}
              </h5>
              <div className="d-flex gap-2">
                {exam && (
                  <Badge bg="secondary">
                    Вопрос {currentQuestionIndex + 1} из {exam.questions?.length || 0}
                  </Badge>
                )}
                <Badge bg="info">Сессия: {currentSession.session_id.slice(-8)}</Badge>
              </div>
            </Card.Header>
            <Card.Body>
              {error && (
                <Alert variant="danger" dismissible onClose={() => {}}>
                  {error}
                </Alert>
              )}

              {questionToDisplay ? (
                <>
                  <div className="mb-4">
                    <h6>Вопрос:</h6>
                    <p className="fs-5">{questionToDisplay.question}</p>
                    {questionToDisplay.type && (
                      <Badge bg="secondary" className="me-2">
                        {questionToDisplay.type}
                      </Badge>
                    )}
                    {questionToDisplay.difficulty && (
                      <Badge bg="info">
                        Сложность: {(questionToDisplay.difficulty * 100).toFixed(0)}%
                      </Badge>
                    )}
                  </div>

                  {evaluation && (
                    <Alert
                      variant={evaluation.is_correct ? 'success' : 'warning'}
                      className="mb-3"
                    >
                      <Alert.Heading>
                        {evaluation.is_correct ? 'Правильно!' : 'Требуется уточнение'}
                      </Alert.Heading>
                      <p>
                        Оценка: {evaluation.score} / {evaluation.max_score}
                      </p>
                      {evaluation.evaluation?.overall_feedback && (
                        <p>{evaluation.evaluation.overall_feedback}</p>
                      )}
                      {evaluation.clarification && (
                        <div className="mt-2">
                          <strong>Уточняющий вопрос:</strong>
                          <p className="mb-0">{evaluation.clarification}</p>
                          <p className="text-muted small mt-2">
                            Подумайте над уточняющим вопросом и попробуйте ответить снова в поле ниже
                          </p>
                        </div>
                      )}
                      {evaluation.error_analysis && (
                        <div className="mt-2">
                          <strong>Анализ ошибки:</strong>
                          <p className="mb-0">{evaluation.error_analysis.error_description}</p>
                        </div>
                      )}
                      {evaluation.is_correct ? (
                        <Button
                          variant="primary"
                          className="mt-2"
                          onClick={handleNextQuestion}
                        >
                          Следующий вопрос
                        </Button>
                      ) : evaluation.clarification ? (
                        <div className="mt-2">
                          <p className="text-muted small">
                            Ответьте на уточняющий вопрос в поле ниже, чтобы продолжить
                          </p>
                        </div>
                      ) : (
                        <p className="text-muted small mt-2">
                          Попробуйте ответить снова
                        </p>
                      )}
                    </Alert>
                  )}

                  <Form onSubmit={handleSubmitAnswer}>
                    <Form.Group className="mb-3">
                      <Form.Label>Ваш ответ:</Form.Label>
                      <Form.Control
                        as="textarea"
                        rows={4}
                        value={answer}
                        onChange={(e) => setAnswer(e.target.value)}
                        disabled={isLoading || (!!evaluation && evaluation.is_correct)}
                        placeholder={
                          evaluation && !evaluation.is_correct && evaluation.clarification
                            ? "Ответьте на уточняющий вопрос..."
                            : "Введите ваш ответ..."
                        }
                      />
                    </Form.Group>
                    <Button
                      type="submit"
                      variant="primary"
                      disabled={!answer.trim() || isLoading || (!!evaluation && evaluation.is_correct) || !questionToDisplay}
                    >
                      {isLoading ? (
                        <>
                          <Spinner animation="border" size="sm" className="me-2" />
                          Оценивается...
                        </>
                      ) : (
                        'Отправить ответ'
                      )}
                    </Button>
                  </Form>
                </>
              ) : (
                <div className="text-center py-5">
                  <p>Загрузка вопроса...</p>
                  <Spinner animation="border" />
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>

        <Col md={4}>
          <Card>
            <Card.Header>
              <div className="d-flex justify-content-between align-items-center">
                <h6 className="mb-0">История диалога</h6>
                <Button
                  variant="outline-primary"
                  size="sm"
                  onClick={handleShowInsights}
                >
                  Аналитика
                </Button>
              </div>
            </Card.Header>
            <Card.Body
              style={{
                maxHeight: '600px',
                overflowY: 'auto',
                backgroundColor: '#f8f9fa',
              }}
            >
              {dialogueHistory.length === 0 ? (
                <p className="text-muted text-center">История диалога пуста</p>
              ) : (
                <div className="d-flex flex-column gap-2">
                  {dialogueHistory.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`p-2 rounded ${
                        msg.sender === 'user'
                          ? 'bg-primary text-white ms-auto'
                          : 'bg-white border'
                      }`}
                      style={{ maxWidth: '90%' }}
                    >
                      <div style={{ fontSize: '0.9rem' }}>{msg.text}</div>
                      {msg.tactic && (
                        <Badge bg="secondary" className="mt-1" style={{ fontSize: '0.7rem' }}>
                          {msg.tactic}
                        </Badge>
                      )}
                      <small
                        className={`d-block mt-1 ${
                          msg.sender === 'user' ? 'text-white-50' : 'text-muted'
                        }`}
                        style={{ fontSize: '0.7rem' }}
                      >
                        {new Date(msg.timestamp).toLocaleTimeString('ru-RU')}
                      </small>
                    </div>
                  ))}
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  )
}

export default ExamSession

