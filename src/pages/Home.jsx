import React, { useState, useEffect } from 'react'
import { Container, Row, Col, Card, Button, ListGroup, InputGroup, Form, Badge, Spinner, Alert } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import { useChat } from '../context/ChatContext'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

const Home = () => {
  const navigate = useNavigate()
  const { chats, createChat, deleteChat } = useChat()
  const { user, isStudent } = useAuth()
  const [searchTerm, setSearchTerm] = useState('')
  const [availableExams, setAvailableExams] = useState([])
  const [examsLoading, setExamsLoading] = useState(false)

  const filteredChats = chats.filter(chat =>
    chat.title.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const handleNewChat = () => {
    const chatId = createChat()
    navigate(`/chat/${chatId}`)
  }

  const handleChatClick = (chatId) => {
    navigate(`/chat/${chatId}`)
  }

  const handleDeleteChat = (e, chatId) => {
    e.stopPropagation()
    if (window.confirm('Вы уверены, что хотите удалить этот диалог?')) {
      deleteChat(chatId)
    }
  }

  useEffect(() => {

    if (isStudent()) {
      loadAvailableExams()
    }
  }, [isStudent])

  const loadAvailableExams = async () => {
    try {
      setExamsLoading(true)
      const response = await api.listExams()
      setAvailableExams(response.exams || [])
    } catch (err) {
      console.error('Failed to load exams:', err)
    } finally {
      setExamsLoading(false)
    }
  }

  const handleExamClick = (examId) => {
    navigate(`/exam/${examId}`)
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    const now = new Date()
    const diff = now - date
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))

    if (days === 0) {
      return 'Сегодня'
    } else if (days === 1) {
      return 'Вчера'
    } else if (days < 7) {
      return `${days} дней назад`
    } else {
      return date.toLocaleDateString('ru-RU')
    }
  }

  return (
    <Container fluid className="py-4">
      <Row>
        <Col md={12} lg={4} xl={3} className="mb-4">
          <Card>
            <Card.Header className="d-flex justify-content-between align-items-center">
              <h5 className="mb-0">
                {isStudent() ? 'Экзамены' : 'История диалогов'}
              </h5>
              {isStudent() && (
                <Button variant="primary" size="sm" onClick={handleNewChat}>
                  + Новый экзамен
                </Button>
              )}
            </Card.Header>
            <Card.Body className="p-0">
              <div className="p-3 border-bottom">
                <InputGroup>
                  <Form.Control
                    type="text"
                    placeholder={isStudent() ? "Поиск экзаменов..." : "Поиск диалогов..."}
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </InputGroup>
              </div>
              <div style={{ maxHeight: 'calc(100vh - 250px)', overflowY: 'auto' }}>
                {isStudent() ? (

                  examsLoading ? (
                    <div className="text-center p-4">
                      <Spinner animation="border" size="sm" />
                      <p className="mt-2 text-muted">Загрузка экзаменов...</p>
                    </div>
                  ) : availableExams.length === 0 ? (
                    <div className="text-center p-4 text-muted">
                      Нет доступных экзаменов. Обратитесь к преподавателю.
                    </div>
                  ) : (
                    <ListGroup variant="flush">
                      {availableExams
                        .filter(exam => 
                          exam.config.name.toLowerCase().includes(searchTerm.toLowerCase())
                        )
                        .map((exam) => (
                          <ListGroup.Item
                            key={exam.exam_id}
                            action
                            onClick={() => handleExamClick(exam.exam_id)}
                            className="d-flex justify-content-between align-items-start"
                            style={{ cursor: 'pointer' }}
                          >
                            <div className="flex-grow-1">
                              <div className="fw-bold">{exam.config.name}</div>
                              <small className="text-muted">
                                {formatDate(exam.created_at)}
                              </small>
                              <div className="mt-1">
                                <Badge bg="info" className="me-1">
                                  {exam.questions?.length || 0} вопросов
                                </Badge>
                                {exam.config.adaptive && (
                                  <Badge bg="success">Адаптивный</Badge>
                                )}
                              </div>
                            </div>
                          </ListGroup.Item>
                        ))}
                    </ListGroup>
                  )
                ) : (

                  filteredChats.length === 0 ? (
                    <div className="text-center p-4 text-muted">
                      {searchTerm
                        ? 'Диалоги не найдены'
                        : 'Нет диалогов в истории'}
                    </div>
                  ) : (
                    <ListGroup variant="flush">
                      {filteredChats.map((chat) => (
                        <ListGroup.Item
                          key={chat.id}
                          action
                          onClick={() => handleChatClick(chat.id)}
                          className="d-flex justify-content-between align-items-start"
                          style={{ cursor: 'pointer' }}
                        >
                          <div className="flex-grow-1">
                            <div className="fw-bold">{chat.title}</div>
                            <small className="text-muted">
                              {formatDate(chat.updatedAt)}
                            </small>
                            {chat.messages.length > 0 && (
                              <div className="text-muted small mt-1" style={{
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                                maxWidth: '200px'
                              }}>
                                {chat.messages[chat.messages.length - 1].text}
                              </div>
                            )}
                          </div>
                          <Button
                            variant="link"
                            size="sm"
                            className="text-danger p-0 ms-2"
                            onClick={(e) => handleDeleteChat(e, chat.id)}
                          >
                            ×
                          </Button>
                        </ListGroup.Item>
                      ))}
                    </ListGroup>
                  )
                )}
              </div>
            </Card.Body>
          </Card>
        </Col>
        <Col md={12} lg={8} xl={9}>
          <Card className="h-100">
            <Card.Body className="d-flex flex-column align-items-center justify-content-center" style={{ minHeight: '500px' }}>
              <div className="text-center">
                <h2 className="mb-4">
                  Добро пожаловать, {user?.name || (isStudent() ? 'Студент' : 'Преподаватель')}!
                </h2>
                {isStudent() ? (
                  <>
                    <p className="text-muted mb-4">
                      Начните новый экзамен с виртуальным экзаменатором или выберите существующий из списка слева
                    </p>
                    {availableExams.length > 0 ? (
                      <p className="text-muted mb-4">
                        Выберите экзамен из списка слева или начните новый диалог
                      </p>
                    ) : (
                      <>
                        <p className="text-muted mb-4">
                          Начните новый экзамен с виртуальным экзаменатором
                        </p>
                        <div className="d-flex gap-2 justify-content-center">
                          <Button variant="primary" size="lg" onClick={handleNewChat}>
                            Начать новый экзамен (Чат)
                          </Button>
                          <Button variant="success" size="lg" onClick={() => navigate('/exam')}>
                            Начать экзамен (Multi-Agent)
                          </Button>
                        </div>
                      </>
                    )}
                  </>
                ) : (
                  <>
                    <p className="text-muted mb-4">
                      Просматривайте историю диалогов студентов или управляйте базой знаний
                    </p>
                    <div className="d-flex gap-2 justify-content-center">
                      <Button variant="primary" size="lg" onClick={() => navigate('/knowledge-base')}>
                        База знаний
                      </Button>
                      <Button variant="outline-primary" size="lg" onClick={() => navigate('/history')}>
                        История
                      </Button>
                    </div>
                  </>
                )}
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  )
}

export default Home

