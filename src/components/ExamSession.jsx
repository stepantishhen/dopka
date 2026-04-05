import React, { useState, useEffect, useRef } from 'react'
import { Container, Row, Col, Form, Button, InputGroup, Spinner, Badge, Alert } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import { useExamSession } from '../context/ExamSessionContext'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

/** Все вопросы экзамена с вариантами — включается входной тест и приветствие. */
function examHasFullMcqPretest(exam) {
  const qs = exam?.questions
  if (!qs?.length) return false
  return qs.every(
    (q) => Array.isArray(q.choices) && q.choices.length >= 2 && q.correct_choice != null
  )
}

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
    completeSession,
    fetchSessionStatus,
    endSession,
    loadDialogueHistory,
  } = useExamSession()

  const [flowPhase, setFlowPhase] = useState('dialogue')
  const [pretestResult, setPretestResult] = useState(null)
  const [mcqIndex, setMcqIndex] = useState(0)
  const [mcqChoices, setMcqChoices] = useState({})
  const [pretestSubmitting, setPretestSubmitting] = useState(false)

  const [answer, setAnswer] = useState('')
  const [evaluation, setEvaluation] = useState(null)
  const [exam, setExam] = useState(null)
  const [examLoading, setExamLoading] = useState(true)
  const [chatMessages, setChatMessages] = useState([])
  const [examResults, setExamResults] = useState(null)
  const [examCompleted, setExamCompleted] = useState(false)
  const [displayedScore, setDisplayedScore] = useState(0)
  const [displayedMax, setDisplayedMax] = useState(0)
  const messagesEndRef = useRef(null)
  const animationRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [chatMessages, dialogueHistory])

  useEffect(() => {
    if (currentSession?.session_id && examId) {
      fetchSessionStatus().then((s) => {
        if (s?.status === 'completed') {
          setExamCompleted(true)
          setExamResults({
            total_score: s.total_score ?? 0,
            max_total_score: s.max_total_score ?? 0,
            questions_answered: s.questions_answered ?? 0,
            passed: s.passed ?? false,
          })
        }
      }).catch(() => {})
    }
  }, [currentSession?.session_id, examId])

  useEffect(() => {
    if (examId) {
      loadExam()
    } else if (!currentSession && user) {
      setExamLoading(false)
      createSession(user.id || `student_${Date.now()}`, null)
        .then(() => {
          const defaultConfig = { num_questions: 10, adaptive: true, unit_ids: null }
          loadNextQuestion(defaultConfig)
        })
        .catch(console.error)
    } else if (!user) {
      setExamLoading(false)
    }
  }, [examId, user])

  useEffect(() => {
    const messages = dialogueHistory.map((msg) => ({
      sender: msg.sender,
      text: msg.text,
      tactic: msg.tactic,
      type: msg.type,
      questionId: msg.question_id,
    }))
    setChatMessages(messages)
  }, [dialogueHistory])

  useEffect(() => {
    const targetScore = dialogueHistory.reduce((s, msg) => {
      const ev = msg.evaluation
      if (ev && ev.is_correct && typeof ev.score === 'number') return s + ev.score
      return s
    }, 0)
    const targetMax = dialogueHistory.reduce((s, msg) => {
      const ev = msg.evaluation
      if (ev && ev.is_correct && typeof ev.max_score === 'number') return s + ev.max_score
      return s
    }, 0)

    if (targetScore === displayedScore && targetMax === displayedMax) return

    const duration = 600
    const startScore = displayedScore
    const startMax = displayedMax
    const startTime = performance.now()

    const tick = (now) => {
      const elapsed = now - startTime
      const t = Math.min(elapsed / duration, 1)
      const ease = 1 - Math.pow(1 - t, 2)
      setDisplayedScore(Math.round(startScore + (targetScore - startScore) * ease))
      setDisplayedMax(Math.round(startMax + (targetMax - startMax) * ease))
      if (t < 1) animationRef.current = requestAnimationFrame(tick)
    }
    animationRef.current = requestAnimationFrame(tick)
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current)
    }
  }, [dialogueHistory])

  const loadExam = async () => {
    if (!examId) {
      setExamLoading(false)
      return
    }
    try {
      setExamLoading(true)
      const examData = await api.getExam(examId)
      if (!examData) throw new Error('Экзамен не найден')
      setExam(examData)

      if (!currentSession && user) {
        try {
          await createSession(user.id || `student_${Date.now()}`, examId)
          const examConfig = {
            num_questions: examData.config?.num_questions || 10,
            adaptive: examData.config?.adaptive !== false,
            unit_ids: examData.config?.unit_ids || null,
          }
          const hasQ = examData.questions?.length > 0
          const adaptive = examData.config?.adaptive !== false
          await loadDialogueHistory()

          if (examHasFullMcqPretest(examData)) {
            setFlowPhase('intro')
            setMcqIndex(0)
            setMcqChoices({})
            setPretestResult(null)
          } else if (hasQ || adaptive) {
            await loadNextQuestion(examConfig)
            setFlowPhase('dialogue')
          }
        } catch (sessionErr) {
          console.error('Failed to create session:', sessionErr)
        }
      }
    } catch (err) {
      console.error('Failed to load exam:', err)
      alert(`Ошибка загрузки экзамена: ${err.message || 'Неизвестная ошибка'}`)
    } finally {
      setExamLoading(false)
    }
  }

  const lastQuestionInDialogue = dialogueHistory.filter((m) => m.type === 'question').pop()
  const questionToAnswer = lastQuestionInDialogue
    ? (exam?.questions?.find((q) => (q.question_id || q.id) === lastQuestionInDialogue.question_id) || {
        question_id: lastQuestionInDialogue.question_id,
        question: lastQuestionInDialogue.text,
        reference_answer: '',
        criteria: [],
      })
    : null

  const handleSubmitAnswer = async (e) => {
    e.preventDefault()
    if (!questionToAnswer) return

    const qId = String(questionToAnswer.question_id ?? questionToAnswer.id ?? '')
    if (!qId) return

    try {
      const result = await submitAnswer(qId, (answer ?? '').trim(), {
        question: questionToAnswer.question,
        reference_answer: questionToAnswer.reference_answer || '',
        criteria: questionToAnswer.criteria || [],
      })
      setEvaluation(result)

      if (result.is_correct) {
        setTimeout(() => moveToNextQuestion(), 2000)
      }
    } catch (err) {
      console.error('Failed to submit answer:', err)
      alert(`Ошибка при отправке ответа: ${err.message}`)
    }
  }

  const startMcqPretest = () => setFlowPhase('mcq')

  const submitPretest = async () => {
    if (!currentSession?.session_id || !exam?.questions?.length) return
    const ids = exam.questions.map((q) => String(q.question_id || q.id))
    for (const id of ids) {
      if (mcqChoices[id] === undefined) {
        alert('Ответьте на все вопросы входного теста')
        return
      }
    }
    setPretestSubmitting(true)
    try {
      const numericChoices = {}
      Object.entries(mcqChoices).forEach(([k, v]) => {
        numericChoices[k] = typeof v === 'number' ? v : parseInt(v, 10)
      })
      const out = await api.completePretest(currentSession.session_id, numericChoices)
      setPretestResult(out)
      setFlowPhase('topics')
    } catch (e) {
      console.error(e)
      alert(e.message || 'Не удалось завершить входной тест')
    } finally {
      setPretestSubmitting(false)
    }
  }

  const handleMcqNext = () => {
    const qs = exam?.questions
    if (!qs?.length) return
    const q = qs[mcqIndex]
    const qid = String(q.question_id || q.id)
    if (mcqChoices[qid] === undefined) return
    if (mcqIndex < qs.length - 1) {
      setMcqIndex((i) => i + 1)
    } else {
      submitPretest()
    }
  }

  const startDialoguePhase = async () => {
    const examConfig = exam
      ? {
          num_questions: exam.config?.num_questions || 10,
          adaptive: exam.config?.adaptive !== false,
          unit_ids: exam.config?.unit_ids || null,
        }
      : { num_questions: 10, adaptive: true, unit_ids: null }
    try {
      await loadNextQuestion(examConfig)
      setFlowPhase('dialogue')
    } catch (e) {
      console.error(e)
      alert(e.message || 'Не удалось начать этап диалога')
    }
  }

  const moveToNextQuestion = () => {
    const examConfig = exam
      ? {
          num_questions: exam.config?.num_questions || 10,
          adaptive: exam.config?.adaptive !== false,
          unit_ids: exam.config?.unit_ids || null,
        }
      : { num_questions: 10, adaptive: true, unit_ids: null }
    setEvaluation(null)
    setAnswer('')
    loadNextQuestion(examConfig)
      .then(() => {})
      .catch(async (err) => {
        if (err?.message?.includes('404') || err?.response?.status === 404) {
          try {
            const result = await completeSession()
            setExamResults(result)
            setExamCompleted(true)
          } catch (e) {
            console.error(e)
            alert('Экзамен завершён!')
            navigate('/')
          }
        } else {
          console.error(err)
        }
      })
  }

  const handleBackAfterExam = () => {
    endSession()
    setExamResults(null)
    setExamCompleted(false)
    navigate('/')
  }

  if (examCompleted && examResults) {
    const { total_score, max_total_score, questions_answered, passed } = examResults
    const percent = max_total_score ? Math.round((total_score / max_total_score) * 100) : 0
    return (
      <Container className="py-5">
        <div className="text-center mx-auto" style={{ maxWidth: 480 }}>
          <h3 className="mb-4">Результаты экзамена</h3>
          <div className="p-4 rounded bg-light border mb-4">
            <p className="mb-2 fs-4">
              Баллы: <strong>{total_score.toFixed(0)}</strong> из <strong>{max_total_score.toFixed(0)}</strong> ({percent}%)
            </p>
            <p className="mb-2">Ответов на вопросы: {questions_answered}</p>
            {passed ? (
              <Badge bg="success" className="fs-6">Экзамен сдан</Badge>
            ) : (
              <Badge bg="secondary" className="fs-6">Экзамен не сдан</Badge>
            )}
          </div>
          <p className="text-muted small">Экзамен завершён. Результаты сохранены для преподавателя.</p>
          <Button variant="primary" size="lg" onClick={handleBackAfterExam}>
            Вернуться на главную
          </Button>
        </div>
      </Container>
    )
  }

  if (examLoading || (examId && !exam && !error)) {
    return (
      <Container className="py-4 d-flex justify-content-center align-items-center" style={{ minHeight: '60vh' }}>
        <div className="text-center">
          <Spinner animation="border" />
          <p className="mt-3">{examLoading ? 'Загрузка экзамена...' : 'Инициализация сессии...'}</p>
        </div>
      </Container>
    )
  }

  if (exam && !currentSession && !user) {
    return (
      <Container className="py-4">
        <Alert variant="warning">Необходимо войти в систему для прохождения экзамена</Alert>
      </Container>
    )
  }

  if (exam && (!exam.questions || exam.questions.length === 0) && !questionToAnswer && !isLoading) {
    return (
      <Container className="py-4">
        <Alert variant="info">В этом экзамене пока нет вопросов. Система генерирует вопросы...</Alert>
        {isLoading && <div className="text-center mt-3"><Spinner animation="border" /></div>}
      </Container>
    )
  }

  if (!examId && !currentSession && user) {
    return (
      <Container className="py-4 d-flex justify-content-center align-items-center" style={{ minHeight: '60vh' }}>
        <div className="text-center">
          <Spinner animation="border" />
          <p className="mt-3">Инициализация сессии...</p>
        </div>
      </Container>
    )
  }

  const allMessages = [...chatMessages]

  const questionCount = dialogueHistory.filter((m) => m.type === 'question').length
  const totalQuestions = exam?.questions?.length ?? null
  const runningScore = dialogueHistory.reduce(
    (acc, msg) => {
      const ev = msg.evaluation
      if (ev && ev.is_correct && typeof ev.score === 'number' && typeof ev.max_score === 'number') {
        return { score: acc.score + ev.score, max: acc.max + ev.max_score }
      }
      return acc
    },
    { score: 0, max: 0 }
  )
  const scorePercent = runningScore.max > 0 ? Math.round((runningScore.score / runningScore.max) * 100) : null

  const hasMcqExam = !!(exam && examHasFullMcqPretest(exam))
  const mcqQ = exam?.questions?.[mcqIndex]
  const mcqN = exam?.questions?.length ?? 0
  const mcqStages = hasMcqExam && ['intro', 'mcq', 'topics'].includes(flowPhase)
  const showDialogueChat = !hasMcqExam || flowPhase === 'intro' || flowPhase === 'dialogue'

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (questionToAnswer && !isLoading && !evaluation?.is_correct) {
        handleSubmitAnswer(e)
      }
    }
  }

  return (
    <Container fluid className="p-0 d-flex flex-column" style={{ height: 'calc(100vh - 56px)', maxWidth: '1400px', overflow: 'hidden' }}>
      <div
        className="border-bottom px-3 py-2 bg-light d-flex justify-content-between align-items-center"
        style={{ flexShrink: 0 }}
      >
        <h6 className="mb-0">{exam ? exam.config?.name : 'Экзамен'}</h6>
      </div>

      <div
        className="d-flex flex-grow-1 overflow-hidden"
        style={{ minHeight: 0, flexWrap: 'nowrap' }}
      >
        <aside
          className="border-end bg-white p-3 flex-shrink-0 overflow-hidden"
          style={{
            width: '260px',
            minWidth: '260px',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <h6 className="text-muted mb-3 small text-uppercase">Для вас</h6>
          {mcqStages ? (
            <>
              <div className="mb-3">
                <div className="fw-semibold">Этап</div>
                <div className="small text-secondary">
                  {flowPhase === 'intro' && 'Приветствие и инструкция'}
                  {flowPhase === 'mcq' && `Входной тест: вопрос ${mcqIndex + 1} из ${mcqN}`}
                  {flowPhase === 'topics' && 'Сводка по темам'}
                </div>
              </div>
              <div className="mb-2 fw-semibold small">Подсказки</div>
              <ul className="small text-secondary ps-3 mb-0" style={{ lineHeight: 1.6 }}>
                {flowPhase === 'intro' && <li>Система сама начинает диалог — прочитайте сообщение и начните тест.</li>}
                {flowPhase === 'mcq' && (
                  <>
                    <li>Выберите один вариант ответа</li>
                    <li>Это поможет упорядочить темы для дальнейшего диалога</li>
                  </>
                )}
                {flowPhase === 'topics' && <li>Ниже — темы, которые стоит подтянуть, и те, где вы увереннее.</li>}
              </ul>
            </>
          ) : (
            <>
              <div className="mb-3">
                <div className="fw-semibold">Прогресс</div>
                <div className="small text-secondary">
                  Вопрос {questionCount} из {totalQuestions ?? '—'}
                </div>
              </div>
              <div className="mb-3">
                <div className="fw-semibold">Текущий набранный балл</div>
                <div className="small">
                  {runningScore.max > 0 ? (
                    <>
                      <strong>{displayedScore}</strong> из {displayedMax}
                      {displayedMax > 0 && (
                        <span className={scorePercent != null && scorePercent >= 56 ? 'text-success' : 'text-secondary'}>
                          {' '}({scorePercent ?? 0}%)
                        </span>
                      )}
                    </>
                  ) : (
                    <span className="text-secondary">{displayedScore}</span>
                  )}
                </div>
              </div>
              <div className="mb-2 fw-semibold small">Подсказки</div>
              <ul className="small text-secondary ps-3 mb-0" style={{ lineHeight: 1.6 }}>
                <li>Отвечайте развёрнуто, своими словами</li>
                <li>Можно сослаться на практику, проекты или опыт — это учитывается в аналитике</li>
                <li>Проходной балл — 56</li>
                <li>При ошибке система даст подсказку и уточняющий вопрос</li>
              </ul>
            </>
          )}
        </aside>

        <div
          className="d-flex flex-column bg-light flex-grow-1 overflow-hidden"
          style={{ minWidth: 0, minHeight: 0 }}
        >
          <div
            className="flex-grow-1 overflow-auto p-3 d-flex justify-content-center"
            style={{ backgroundColor: '#f8f9fa', minHeight: 0 }}
          >
            <div style={{ width: '100%', maxWidth: '720px' }}>
              {error && <Alert variant="danger" dismissible>{error}</Alert>}

              {flowPhase === 'topics' && pretestResult && (
                <div className="bg-white border rounded p-4 shadow-sm">
                  <h5 className="mb-3">Сводка по темам</h5>
                  <p className="text-muted small mb-4">
                    Ниже — темы, где ответы совпали с ключом, и темы, которые лучше проработать в диалоге.
                    Дальше вы перейдёте к развёрнутым ответам: система подскажет, пока ответ не будет засчитан верным.
                  </p>
                  <Row className="g-3 mb-2">
                    <Col md={6}>
                      <div className="p-3 rounded border border-success bg-success bg-opacity-10 h-100">
                        <div className="fw-semibold text-success mb-2">Сейчас увереннее</div>
                        {pretestResult.strong_topics?.length ? (
                          <ul className="small mb-0 ps-3">
                            {pretestResult.strong_topics.map((t) => (
                              <li key={t.topic}>
                                {t.topic} ({t.correct}/{t.total})
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="small text-muted mb-0">Нет тем без ошибок во входном тесте</p>
                        )}
                      </div>
                    </Col>
                    <Col md={6}>
                      <div className="p-3 rounded border border-warning bg-warning bg-opacity-10 h-100">
                        <div className="fw-semibold text-dark mb-2">Стоит подтянуть</div>
                        {pretestResult.weak_topics?.length ? (
                          <ul className="small mb-0 ps-3">
                            {pretestResult.weak_topics.map((t) => (
                              <li key={t.topic}>
                                {t.topic} ({t.correct}/{t.total})
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="small text-muted mb-0">Отлично: по всем темам верные ответы</p>
                        )}
                      </div>
                    </Col>
                  </Row>
                </div>
              )}

              {flowPhase === 'mcq' && mcqQ && (
                <div className="bg-white border rounded p-4 shadow-sm">
                  <Badge bg="secondary" className="mb-2">
                    Входной тест · {mcqIndex + 1} / {mcqN}
                  </Badge>
                  {mcqQ.topic && (
                    <div className="text-muted small mb-2">Тема: {mcqQ.topic}</div>
                  )}
                  <h5 className="mb-4">{mcqQ.question}</h5>
                  <div className="d-flex flex-column gap-2">
                    {mcqQ.choices.map((label, idx) => {
                      const qid = String(mcqQ.question_id || mcqQ.id)
                      return (
                        <Form.Check
                          key={idx}
                          type="radio"
                          name={`mcq-${qid}`}
                          id={`mcq-${qid}-${idx}`}
                          label={label}
                          checked={mcqChoices[qid] === idx}
                          onChange={() => setMcqChoices((prev) => ({ ...prev, [qid]: idx }))}
                        />
                      )
                    })}
                  </div>
                </div>
              )}

              {showDialogueChat && (
                <>
                  {allMessages.length === 0 ? (
                    <div className="text-center text-muted py-5">
                      {flowPhase === 'intro' ? (
                        <>
                          <Spinner animation="border" size="sm" className="me-2" />
                          <p className="mt-2 mb-0">Загрузка приветствия…</p>
                        </>
                      ) : (
                        <>
                          <h5>Начало экзамена</h5>
                          <p>Ответьте на вопрос в поле ниже</p>
                        </>
                      )}
                    </div>
                  ) : (
                    <div className="d-flex flex-column gap-3">
                      {allMessages.map((msg, idx) => (
                        <div
                          key={idx}
                          className={`d-flex ${msg.sender === 'user' ? 'justify-content-end' : 'justify-content-start'}`}
                        >
                          <div
                            className={`p-3 rounded ${
                              msg.sender === 'user'
                                ? 'bg-primary text-white'
                                : msg.type === 'question'
                                ? 'bg-white border border-primary'
                                : msg.type === 'welcome'
                                ? 'bg-white border border-primary border-2'
                                : 'bg-white border'
                            }`}
                            style={{ maxWidth: '85%' }}
                          >
                            {msg.type === 'welcome' && (
                              <Badge bg="primary" className="mb-1" style={{ fontSize: '0.65rem' }}>
                                Система
                              </Badge>
                            )}
                            {msg.type === 'question' && (
                              <Badge bg="info" className="mb-1" style={{ fontSize: '0.65rem' }}>
                                Вопрос
                              </Badge>
                            )}
                            <div className="mb-1">{msg.text}</div>
                            {msg.tactic && (
                              <Badge bg="secondary" className="me-1" style={{ fontSize: '0.65rem' }}>{msg.tactic}</Badge>
                            )}
                            <small
                              className={`d-block mt-1 ${msg.sender === 'user' ? 'text-white-50' : 'text-muted'}`}
                              style={{ fontSize: '0.7rem' }}
                            >
                              {new Date().toLocaleTimeString('ru-RU')}
                            </small>
                          </div>
                        </div>
                      ))}
                      {evaluation?.is_correct && (
                        <div className="d-flex justify-content-start">
                          <div className="p-3 rounded bg-success bg-opacity-25 border border-success">
                            <strong>Правильно!</strong>
                            {evaluation.evaluation?.overall_feedback && (
                              <p className="mb-0 mt-1 small">{evaluation.evaluation.overall_feedback}</p>
                            )}
                            <Button size="sm" variant="success" className="mt-2" onClick={moveToNextQuestion}>
                              Следующий вопрос
                            </Button>
                          </div>
                        </div>
                      )}
                      {isLoading && (
                        <div className="d-flex justify-content-start">
                          <div className="bg-white border p-3 rounded">
                            <Spinner animation="border" size="sm" className="me-2" />
                            <span className="text-muted">Оценивается...</span>
                          </div>
                        </div>
                      )}
                      <div ref={messagesEndRef} />
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="border-top bg-white p-3" style={{ flexShrink: 0 }}>
            <div style={{ maxWidth: '720px', margin: '0 auto' }}>
              {flowPhase === 'intro' && hasMcqExam && (
                <div className="d-flex justify-content-end">
                  <Button variant="primary" size="lg" onClick={startMcqPretest}>
                    Начать входной тест
                  </Button>
                </div>
              )}
              {flowPhase === 'mcq' && mcqQ && (
                <div className="d-flex justify-content-between align-items-center gap-2 flex-wrap">
                  <Button variant="outline-secondary" disabled={mcqIndex === 0} onClick={() => setMcqIndex((i) => Math.max(0, i - 1))}>
                    Назад
                  </Button>
                  <Button
                    variant="primary"
                    disabled={
                      pretestSubmitting ||
                      mcqChoices[String(mcqQ.question_id || mcqQ.id)] === undefined
                    }
                    onClick={handleMcqNext}
                  >
                    {pretestSubmitting ? (
                      <>
                        <Spinner animation="border" size="sm" className="me-2" />
                        Отправка…
                      </>
                    ) : mcqIndex < mcqN - 1 ? (
                      'Далее'
                    ) : (
                      'Завершить тест'
                    )}
                  </Button>
                </div>
              )}
              {flowPhase === 'topics' && pretestResult && (
                <div className="d-flex justify-content-end">
                  <Button variant="success" size="lg" onClick={startDialoguePhase} disabled={isLoading}>
                    {isLoading ? <Spinner animation="border" size="sm" /> : 'Перейти к диалогу'}
                  </Button>
                </div>
              )}
              {(flowPhase === 'dialogue' || !hasMcqExam) && (
                <Form onSubmit={handleSubmitAnswer}>
                  <InputGroup>
                    <Form.Control
                      as="textarea"
                      rows={2}
                      placeholder={
                        evaluation && !evaluation.is_correct && evaluation.clarification
                          ? 'Ответьте на уточняющий вопрос...'
                          : 'Введите ваш ответ... (Enter — отправить, Shift+Enter — новая строка)'
                      }
                      value={answer}
                      onChange={(e) => setAnswer(e.target.value)}
                      onKeyDown={handleKeyDown}
                      disabled={isLoading || (!!evaluation?.is_correct)}
                      style={{ resize: 'none' }}
                    />
                    <Button
                      type="submit"
                      variant="primary"
                      disabled={isLoading || !!evaluation?.is_correct || !questionToAnswer}
                    >
                      {isLoading ? <Spinner animation="border" size="sm" /> : 'Отправить'}
                    </Button>
                  </InputGroup>
                </Form>
              )}
            </div>
          </div>
        </div>
      </div>
    </Container>
  )
}

export default ExamSession
