import React, { useState, useEffect } from 'react'
import { Container, Card, Button, Table, Badge, Alert, Spinner, InputGroup, Form, OverlayTrigger, Tooltip } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

const Exams = () => {
  const navigate = useNavigate()
  const [exams, setExams] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [creatingSample, setCreatingSample] = useState(false)
  const [copiedCode, setCopiedCode] = useState(null)
  const [importingStudents, setImportingStudents] = useState(false)

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

  const handleCreateSample = async () => {
    setCreatingSample(true)
    try {
      const exam = await api.createSampleExam()
      setExams(prev => [exam, ...prev])
      navigate(`/exam/${exam.exam_id}`)
    } catch (err) {
      setError(err.message || 'Ошибка создания тестового экзамена')
    } finally {
      setCreatingSample(false)
    }
  }

  const copyJoinLink = (exam) => {
    const path = exam.join_path || (exam.join_code ? `/join/${exam.join_code}` : '')
    if (!path) return
    const url = `${window.location.origin}${path.startsWith('/') ? path : `/${path}`}`
    navigator.clipboard?.writeText(url).then(() => {
      setCopiedCode(exam.join_code)
      setTimeout(() => setCopiedCode(null), 2000)
    }).catch(() => {})
  }

  const handleViewExam = (examId) => {
    navigate(`/exam/${examId}`)
  }

  const handleImportStudents = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImportingStudents(true)
    try {
      const r = await api.importStudentsCsv(file)
      const msg = `Создано учётных записей: ${r.created?.length ?? 0}, пропущено: ${r.skipped?.length ?? 0}.`
      const pwdHint =
        r.created?.length > 0
          ? `\n\nВременные пароли показаны в ответе сервера (сохраните). Первая запись: ${r.created[0].email}`
          : ''
      alert(msg + pwdHint + '\n\nПодробности в консоли разработчика (Network).')
      console.info('import_students', r)
    } catch (err) {
      setError(err.message || 'Ошибка импорта CSV')
    } finally {
      setImportingStudents(false)
      e.target.value = ''
    }
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
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-2">
        <h2 className="mb-0">Экзамены</h2>
        <div className="d-flex flex-wrap gap-2 align-items-center">
          <Button
            variant="outline-success"
            onClick={handleCreateSample}
            disabled={creatingSample}
          >
            {creatingSample ? <Spinner animation="border" size="sm" /> : null} Тестовый экзамен
          </Button>
          <Button variant="primary" onClick={() => navigate('/knowledge-base')}>
            Создать из материалов
          </Button>
          <Form.Control
            type="file"
            accept=".csv,text/csv"
            disabled={importingStudents}
            onChange={handleImportStudents}
            style={{ maxWidth: 220 }}
            title="Импорт студентов: CSV с колонками email, name"
          />
          {importingStudents && <Spinner animation="border" size="sm" />}
        </div>
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
                  <th>Код</th>
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
                    <td>
                      {exam.join_code ? (
                        <InputGroup size="sm" style={{ maxWidth: 150 }}>
                          <Form.Control
                            readOnly
                            value={exam.join_code}
                            className="text-uppercase"
                          />
                          <OverlayTrigger
                            placement="top"
                            overlay={<Tooltip>{copiedCode === exam.join_code ? 'Скопировано!' : 'Скопировать ссылку'}</Tooltip>}
                          >
                            <Button
                              variant="outline-secondary"
                              size="sm"
                              onClick={() => copyJoinLink(exam)}
                            >
                              📋
                            </Button>
                          </OverlayTrigger>
                        </InputGroup>
                      ) : '-'}
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

