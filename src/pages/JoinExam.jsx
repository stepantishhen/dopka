import React, { useState, useEffect } from 'react'
import { Container, Row, Col, Card, Button, Form, InputGroup, Alert, Spinner } from 'react-bootstrap'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

const JoinExam = () => {
  const { code } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [joinCode, setJoinCode] = useState(code || '')
  const [exam, setExam] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadExamByCode = async (codeToTry) => {
    if (!codeToTry?.trim()) return
    setLoading(true)
    setError(null)
    try {
      const examData = await api.getExamByJoinCode(codeToTry.trim())
      setExam(examData)
    } catch (err) {
      setError('Экзамен с таким кодом не найден')
      setExam(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (code) {
      loadExamByCode(code)
    }
  }, [code])

  const handleJoin = (e) => {
    e?.preventDefault()
    if (joinCode.trim()) {
      loadExamByCode(joinCode)
    }
  }

  const handleStartExam = () => {
    if (exam) {
      navigate(`/exam/${exam.exam_id}`)
    }
  }

  if (!user) {
    return (
      <Container className="py-5">
        <Card className="text-center">
          <Card.Body>
            <p>Для присоединения к экзамену необходимо войти в систему</p>
            <Button variant="primary" onClick={() => navigate(`/login?join=${code || joinCode || ''}`)}>
              Войти
            </Button>
          </Card.Body>
        </Card>
      </Container>
    )
  }

  return (
    <Container className="py-5">
      <Row className="justify-content-center">
        <Col md={8} lg={6}>
          <Card>
            <Card.Header>
              <h4 className="mb-0">Присоединиться к экзамену</h4>
            </Card.Header>
            <Card.Body>
              {!code && (
                <Form onSubmit={handleJoin} className="mb-4">
                  <p className="text-muted small mb-2">
                    Код тестового экзамена (5 вопросов): <strong>TEST01</strong>
                  </p>
                  <Form.Label>Код экзамена</Form.Label>
                  <InputGroup>
                    <Form.Control
                      type="text"
                      placeholder="ABC123"
                      value={joinCode}
                      onChange={(e) => setJoinCode(e.target.value.toUpperCase().slice(0, 6))}
                      maxLength={6}
                      style={{ textTransform: 'uppercase' }}
                    />
                    <Button variant="primary" onClick={handleJoin} disabled={loading || joinCode.length < 6}>
                      {loading ? <Spinner animation="border" size="sm" /> : 'Найти'}
                    </Button>
                  </InputGroup>
                </Form>
              )}
              {error && <Alert variant="danger">{error}</Alert>}
              {exam && (
                <div>
                  <h5>{exam.config?.name}</h5>
                  <p className="text-muted">Вопросов: {exam.questions?.length || 0}</p>
                  <Button variant="success" size="lg" onClick={handleStartExam}>
                    Начать экзамен
                  </Button>
                </div>
              )}
              {code && loading && (
                <div className="text-center py-4">
                  <Spinner animation="border" />
                  <p className="mt-2">Загрузка экзамена...</p>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  )
}

export default JoinExam
