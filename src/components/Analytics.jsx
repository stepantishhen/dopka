import React, { useState, useEffect } from 'react'
import { Container, Row, Col, Card, Spinner, Alert, ListGroup, Button, Badge } from 'react-bootstrap'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'

const Analytics = () => {
  const { user } = useAuth()
  const staff = user && (user.role === 'teacher' || user.role === 'admin')
  const [metrics, setMetrics] = useState(null)
  const [students, setStudents] = useState([])
  const [selectedStudentId, setSelectedStudentId] = useState(null)
  const [studentAnalytics, setStudentAnalytics] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [studentsLoading, setStudentsLoading] = useState(false)
  const [analyticsLoading, setAnalyticsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [studentsError, setStudentsError] = useState(null)
  const [monitoring, setMonitoring] = useState(null)
  const [monitoringLoading, setMonitoringLoading] = useState(false)
  const [exportBusy, setExportBusy] = useState(false)
  const [byExam, setByExam] = useState(null)
  const [byExamLoading, setByExamLoading] = useState(false)

  useEffect(() => {
    loadMetrics()
    if (staff) loadStudents()
  }, [staff])

  useEffect(() => {
    if (!staff) return
    let cancelled = false
    const run = async () => {
      try {
        setByExamLoading(true)
        const data = await api.getTeacherAnalyticsByExam()
        if (!cancelled) setByExam(data?.exams || [])
      } catch {
        if (!cancelled) setByExam(null)
      } finally {
        if (!cancelled) setByExamLoading(false)
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [staff])

  useEffect(() => {
    if (staff && selectedStudentId) {
      loadStudentAnalytics(selectedStudentId)
    } else {
      setStudentAnalytics(null)
    }
  }, [staff, selectedStudentId])

  useEffect(() => {
    if (!staff) return
    let cancelled = false
    const loadMonitoring = async () => {
      try {
        setMonitoringLoading(true)
        const data = await api.getTeacherMonitoringSessions()
        if (!cancelled) setMonitoring(data)
      } catch {
        if (!cancelled) setMonitoring(null)
      } finally {
        if (!cancelled) setMonitoringLoading(false)
      }
    }
    loadMonitoring()
    const t = setInterval(loadMonitoring, 15000)
    return () => {
      cancelled = true
      clearInterval(t)
    }
  }, [staff])

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
    if (!staff) return
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

  if (isLoading && !staff) {
    return (
      <Container className="py-4">
        <div className="text-center">
          <Spinner animation="border" />
        </div>
      </Container>
    )
  }

  if (error && !staff) {
    return (
      <Container className="py-4">
        <Alert variant="danger">{error}</Alert>
      </Container>
    )
  }

  return (
    <Container className="py-4">
      <h2 className="mb-4">
        {staff ? 'Аналитика по студентам' : 'Аналитика системы'}
      </h2>

      {staff && (
        <Row className="mb-3">
          <Col>
            <Card className="mb-3">
              <Card.Header>Сводка по экзаменам</Card.Header>
              <Card.Body>
                {byExamLoading ? (
                  <Spinner animation="border" size="sm" />
                ) : byExam?.length ? (
                  <div className="table-responsive">
                    <table className="table table-sm mb-0">
                      <thead>
                        <tr>
                          <th>Экзамен (id)</th>
                          <th>Прохождений</th>
                          <th>Средний %</th>
                          <th>Упоминаний практики</th>
                        </tr>
                      </thead>
                      <tbody>
                        {byExam.map((row) => (
                          <tr key={row.exam_id || '_none'}>
                            <td>
                              <small className="text-muted">{row.exam_id || '—'}</small>
                            </td>
                            <td>{row.sessions_count}</td>
                            <td>{row.avg_percent != null ? `${row.avg_percent}%` : '—'}</td>
                            <td>{row.practical_mentions}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <span className="text-muted">Нет данных по завершённым сессиям</span>
                )}
              </Card.Body>
            </Card>
            <div className="d-flex flex-wrap gap-2 align-items-center mb-2">
              <Button
                variant="outline-primary"
                size="sm"
                disabled={exportBusy}
                onClick={async () => {
                  try {
                    setExportBusy(true)
                    const data = await api.exportAnalyticsJson()
                    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
                    const a = document.createElement('a')
                    a.href = URL.createObjectURL(blob)
                    a.download = `analytics_export_${new Date().toISOString().slice(0, 10)}.json`
                    a.click()
                    URL.revokeObjectURL(a.href)
                  } catch (e) {
                    alert(e.message || 'Ошибка экспорта')
                  } finally {
                    setExportBusy(false)
                  }
                }}
              >
                Экспорт JSON
              </Button>
              <Button
                variant="outline-secondary"
                size="sm"
                disabled={exportBusy}
                onClick={async () => {
                  try {
                    setExportBusy(true)
                    await api.downloadAnalyticsCsv()
                  } catch (e) {
                    alert(e.message || 'Ошибка экспорта CSV')
                  } finally {
                    setExportBusy(false)
                  }
                }}
              >
                Экспорт CSV
              </Button>
            </div>
            <Card className="mb-3">
              <Card.Header>Активные сессии экзаменов</Card.Header>
              <Card.Body>
                {monitoringLoading ? (
                  <Spinner animation="border" size="sm" />
                ) : monitoring?.sessions?.length ? (
                  <ListGroup variant="flush">
                    {monitoring.sessions.map((s) => (
                      <ListGroup.Item key={s.session_id}>
                        <small className="text-muted">{s.session_id}</small>
                        <div>
                          Студент: {s.student_id}
                          {s.exam_id && ` · Экзамен: ${s.exam_id}`}
                        </div>
                        <small>
                          Вопросов: {s.questions_answered ?? 0} · Реплик: {s.dialogue_turns ?? 0} · {s.status}
                        </small>
                      </ListGroup.Item>
                    ))}
                  </ListGroup>
                ) : (
                  <span className="text-muted">Нет активных сессий</span>
                )}
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}

      {staff && (
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

      {(!staff || metrics) && (
        <>
          <h5 className="mt-4 mb-3">{staff ? 'Метрики системы' : ''}</h5>
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
