import React, { useState, useEffect } from 'react'
import { Container, Card, Button, Table, Badge, Alert, Spinner } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

const Exams = () => {
  const navigate = useNavigate()
  const [exams, setExams] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadExams()
  }, [])

  const loadExams = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await api.listExams()
      setExams(response.exams || [])
    } catch (err) {
      setError(err.message || 'Ошибка при загрузке экзаменов')
    } finally {
      setIsLoading(false)
    }
  }

  const handleViewExam = (examId) => {
    navigate(`/exam/${examId}`)
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    return date.toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (isLoading) {
    return (
      <Container className="py-4">
        <div className="text-center">
          <Spinner animation="border" />
          <p className="mt-3">Загрузка экзаменов...</p>
        </div>
      </Container>
    )
  }

  return (
    <Container className="py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>Экзамены</h2>
        <Button variant="primary" onClick={() => navigate('/knowledge-base')}>
          Создать экзамен из материалов
        </Button>
      </div>

      {error && (
        <Alert variant="danger" dismissible onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {exams.length === 0 ? (
        <Alert variant="info" className="text-center">
          Нет созданных экзаменов. Создайте первый экзамен из материалов!
        </Alert>
      ) : (
        <Card>
          <Card.Body className="p-0">
            <Table striped bordered hover responsive>
              <thead>
                <tr>
                  <th>Название</th>
                  <th>Статус</th>
                  <th>Вопросов</th>
                  <th>Адаптивный</th>
                  <th>Создан</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {exams.map((exam) => (
                  <tr key={exam.exam_id}>
                    <td>
                      <strong>{exam.config.name}</strong>
                    </td>
                    <td>
                      <Badge bg={exam.status === 'active' ? 'success' : 'secondary'}>
                        {exam.status}
                      </Badge>
                    </td>
                    <td>{exam.questions?.length || 0}</td>
                    <td>
                      {exam.config.adaptive ? (
                        <Badge bg="info">Да</Badge>
                      ) : (
                        <Badge bg="secondary">Нет</Badge>
                      )}
                    </td>
                    <td>{formatDate(exam.created_at)}</td>
                    <td>
                      <Button
                        variant="outline-primary"
                        size="sm"
                        onClick={() => handleViewExam(exam.exam_id)}
                      >
                        Просмотр
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Card.Body>
        </Card>
      )}
    </Container>
  )
}

export default Exams

