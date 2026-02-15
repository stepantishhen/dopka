import React, { useState, useEffect } from 'react'
import { Container, Row, Col, Card, Spinner, Alert, ListGroup, Button, Badge } from 'react-bootstrap'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'

const Analytics = () => {
  const { user } = useAuth()
  const [metrics, setMetrics] = useState(null)
  const [students, setStudents] = useState([])
  const [selectedStudentId, setSelectedStudentId] = useState(null)
  const [studentAnalytics, setStudentAnalytics] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [studentsLoading, setStudentsLoading] = useState(false)
  const [analyticsLoading, setAnalyticsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [studentsError, setStudentsError] = useState(null)

  const isTeacher = user?.role === 'teacher'

  useEffect(() => {
    loadMetrics()
    if (isTeacher) loadStudents()
  }, [isTeacher])

  useEffect(() => {
    if (isTeacher && selectedStudentId) {
      loadStudentAnalytics(selectedStudentId)
    } else {
      setStudentAnalytics(null)
    }
  }, [isTeacher, selectedStudentId])

  const loadMetrics = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await api.getMetrics()
      setMetrics(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const loadStudents = async () => {
    if (!isTeacher) return
    try {
      setStudentsLoading(true)
      setStudentsError(null)
      const data = await api.getTeacherStudents()
      setStudents(data.students || [])
    } catch (err) {
      setStudentsError(err.message || 'Не удалось загрузить список студентов')
      setStudents([])
    } finally {
      setStudentsLoading(false)
    }
  }

  const loadStudentAnalytics = async (studentId) => {
    try {
      setAnalyticsLoading(true)
      const data = await api.getStudentAnalytics(studentId)
      setStudentAnalytics(data)
    } catch (err) {
      console.error('Failed to load student analytics:', err)
      setStudentAnalytics(null)
    } finally {
      setAnalyticsLoading(false)
    }
  }

  if (isLoading && !isTeacher) {
    return (
      <Container className="py-4">
        <div className="text-center">
          <Spinner animation="border" />
        </div>
      </Container>
    )
  }

  if (error && !isTeacher) {
    return (
      <Container className="py-4">
        <Alert variant="danger">{error}</Alert>
      </Container>
    )
  }

  return (
    <Container className="py-4">
      <h2 className="mb-4">
        {isTeacher ? 'Аналитика по студентам' : 'Аналитика системы'}
      </h2>

      {isTeacher && (
        <Row className="mb-4">
          <Col md={4}>
            <Card>
              <Card.Header>Студенты</Card.Header>
              <Card.Body className="p-0">
                {studentsLoading ? (
                  <div className="p-3 text-center">
                    <Spinner animation="border" size="sm" />
                  </div>
                ) : studentsError ? (
                  <div className="p-3">
                    <Alert variant="warning" className="mb-0">{studentsError}</Alert>
                  </div>
                ) : students.length === 0 ? (
                  <div className="p-3 text-muted">Нет данных об ответах студентов</div>
                ) : (
                  <ListGroup variant="flush">
                    {students.map((s) => (
                      <ListGroup.Item
                        key={s.student_id}
                        action
                        active={selectedStudentId === s.student_id}
                        onClick={() => setSelectedStudentId(s.student_id)}
                      >
                        <div className="d-flex justify-content-between align-items-center">
                          <span>{s.name || s.student_id}</span>
                          {s.last_total_score != null && s.last_max_total_score != null && (
                            <Badge bg="secondary">
                              {s.last_total_score.toFixed(0)} / {s.last_max_total_score.toFixed(0)}
                            </Badge>
                          )}
                        </div>
                        {s.last_updated_at && (
                          <small className="text-muted">
                            {new Date(s.last_updated_at).toLocaleDateString('ru-RU')}
                          </small>
                        )}
                      </ListGroup.Item>
                    ))}
                  </ListGroup>
                )}
              </Card.Body>
            </Card>
          </Col>
          <Col md={8}>
            {selectedStudentId && (
              <Card>
                <Card.Header>
                  Аналитика: {students.find((s) => s.student_id === selectedStudentId)?.name || selectedStudentId}
                </Card.Header>
                <Card.Body>
                  {analyticsLoading ? (
                    <div className="text-center py-4">
                      <Spinner animation="border" />
                    </div>
                  ) : studentAnalytics?.sessions?.length ? (
                    <div className="d-flex flex-column gap-3">
                      {studentAnalytics.sessions.map((session, idx) => (
                        <Card key={session.session_id || idx} className="border">
                          <Card.Body>
                            <div className="d-flex justify-content-between mb-2">
                              <small className="text-muted">
                                Сессия: {session.session_id?.slice(0, 12)}…
                                {session.exam_id && ` · Экзамен: ${session.exam_id}`}
                              </small>
                              {(session.total_score != null && session.max_total_score != null) && (
                                <>
                                  <Badge bg="primary" className="me-1">
                                    {session.total_score.toFixed(0)} / {session.max_total_score.toFixed(0)}
                                  </Badge>
                                  {(session.total_score / session.max_total_score) >= 0.56 && (
                                    <Badge bg="success">Сдан</Badge>
                                  )}
                                </>
                              )}
                            </div>
                            <div className="mb-2">
                              <strong>Вопросов:</strong> {session.questions_answered ?? session.metrics?.length ?? 0}
                            </div>
                            {session.insights && Object.keys(session.insights).length > 0 && (
                              <div className="mt-2">
                                <strong>Инсайты:</strong>
                                {session.insights.key_insights?.length > 0 && (
                                  <ul className="mb-1 mt-1">
                                    {session.insights.key_insights.map((item, i) => (
                                      <li key={i}>{item}</li>
                                    ))}
                                  </ul>
                                )}
                                {session.insights.recommendations?.length > 0 && (
                                  <div>
                                    <strong>Рекомендации:</strong>
                                    <ul className="mb-0">
                                      {session.insights.recommendations.map((item, i) => (
                                        <li key={i}>{item}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            )}
                            {session.created_at && (
                              <small className="text-muted d-block mt-2">
                                {new Date(session.created_at).toLocaleString('ru-RU')}
                              </small>
                            )}
                          </Card.Body>
                        </Card>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted mb-0">Нет сессий для этого студента</p>
                  )}
                </Card.Body>
              </Card>
            )}
          </Col>
        </Row>
      )}

      {(!isTeacher || metrics) && (
        <>
          <h5 className="mt-4 mb-3">{isTeacher ? 'Метрики системы' : ''}</h5>
          {metrics && (
            <Row className="mb-4">
              <Col md={4}>
                <Card>
                  <Card.Header>API Запросы</Card.Header>
                  <Card.Body>
                    <h5>{metrics.api_requests?.total || 0}</h5>
                    <p className="text-muted mb-0">
                      Среднее время ответа:{' '}
                      {metrics.api_requests?.avg_response_time_ms
                        ? `${metrics.api_requests.avg_response_time_ms.toFixed(2)} мс`
                        : 'N/A'}
                    </p>
                    {metrics.api_requests?.status_codes && (
                      <div className="mt-2">
                        {Object.entries(metrics.api_requests.status_codes).map(([code, count]) => (
                          <span key={code} className="badge bg-secondary me-1">
                            {code}: {count}
                          </span>
                        ))}
                      </div>
                    )}
                  </Card.Body>
                </Card>
              </Col>
              <Col md={4}>
                <Card>
                  <Card.Header>Вызовы агентов</Card.Header>
                  <Card.Body>
                    <h5>{metrics.agent_calls?.total || 0}</h5>
                    {metrics.agent_calls?.by_agent && (
                      <div className="mt-2">
                        {Object.entries(metrics.agent_calls.by_agent).map(([agent, stats]) => (
                          <div key={agent} className="mb-2">
                            <strong>{agent}:</strong> Всего: {stats.total}, Успешно:{' '}
                            {stats.success}, Ошибок: {stats.failed}
                          </div>
                        ))}
                      </div>
                    )}
                  </Card.Body>
                </Card>
              </Col>
              <Col md={4}>
                <Card>
                  <Card.Header>Ошибки</Card.Header>
                  <Card.Body>
                    <h5>{metrics.errors?.total || 0}</h5>
                    {metrics.errors?.recent && metrics.errors.recent.length > 0 && (
                      <div className="mt-2">
                        <strong>Последние ошибки:</strong>
                        <ul className="mt-2">
                          {metrics.errors.recent.slice(0, 5).map((err, idx) => (
                            <li key={idx} style={{ fontSize: '0.9rem' }}>
                              [{err.error_type}] {err.message}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          )}
        </>
      )}
    </Container>
  )
}

export default Analytics
