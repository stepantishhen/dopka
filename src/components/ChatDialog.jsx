import React, { useState, useEffect, useRef } from 'react'
import { Container, Row, Col, Card, Form, Button, InputGroup, Spinner, Badge, Alert } from 'react-bootstrap'
import { useParams, useNavigate } from 'react-router-dom'
import { useChat } from '../context/ChatContext'
import { useExamSession } from '../context/ExamSessionContext'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

const ChatDialog = () => {
  const { chatId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { getChat, createChat, addMessage, updateChatTitle } = useChat()
  const { currentSession, dialogueHistory, submitAnswer, loadNextQuestion, createSession } = useExamSession()
  const [message, setMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [useOrchestrator, setUseOrchestrator] = useState(true) 
  const messagesEndRef = useRef(null)
  const chat = chatId ? getChat(chatId) : null

  useEffect(() => {
    if (!chatId) {
      const newChatId = createChat()
      navigate(`/chat/${newChatId}`, { replace: true })
    }
    

    if (useOrchestrator && !currentSession && user) {
      createSession(user.id || `student_${Date.now()}`)
        .catch(err => {
          console.error('Failed to create session:', err)
          setUseOrchestrator(false) 
        })
    }
  }, [chatId, createChat, navigate, useOrchestrator, currentSession, user, createSession])

  useEffect(() => {
    scrollToBottom()
  }, [chat?.messages, dialogueHistory])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleSend = async (e) => {
    e.preventDefault()
    if (!message.trim() || !chat) return

    const userMessage = {
      id: Date.now().toString(),
      text: message,
      sender: 'user',
      timestamp: new Date().toISOString()
    }

    addMessage(chat.id, userMessage)
    setMessage('')
    setIsLoading(true)
    setError(null)

    try {
      if (useOrchestrator && currentSession) {


        const response = await api.sendMessage(chat.id, message)
        
        const aiMessage = {
          id: (Date.now() + 1).toString(),
          text: response.messages[response.messages.length - 1]?.text || 'Ответ получен',
          sender: 'ai',
          timestamp: new Date().toISOString()
        }
        addMessage(chat.id, aiMessage)
      } else {

        setTimeout(() => {
          const aiMessage = {
            id: (Date.now() + 1).toString(),
            text: generateAIResponse(message),
            sender: 'ai',
            timestamp: new Date().toISOString()
          }
          addMessage(chat.id, aiMessage)
          
          if (chat.messages.length === 0) {
            const title = message.length > 30 ? message.substring(0, 30) + '...' : message
            updateChatTitle(chat.id, title)
          }
        }, 1000 + Math.random() * 1000)
      }
    } catch (err) {
      setError(err.message)
      console.error('Failed to send message:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const generateAIResponse = (userMessage) => {

    const examResponses = [
      `Хороший вопрос! Давайте разберем это подробнее. Что вы думаете о "${userMessage}"?`,
      `Интересно. Можете ли вы объяснить ваше понимание "${userMessage}" более детально?`,
      `Это важная тема. Как бы вы применили знания о "${userMessage}" на практике?`,
      `Хорошо. Теперь давайте углубимся. Что еще вы знаете о "${userMessage}"?`,
      `Правильно. А теперь подумайте: какие еще аспекты "${userMessage}" вы можете выделить?`
    ]
    return examResponses[Math.floor(Math.random() * examResponses.length)]
  }

  if (!chat) {
    return (
      <Container className="py-4">
        <div className="text-center">
          <Spinner animation="border" />
        </div>
      </Container>
    )
  }

  return (
    <Container fluid className="py-4">
      <Row>
        <Col md={12}>
          <Card className="h-100">
            <Card.Header className="d-flex justify-content-between align-items-center">
              <h5 className="mb-0">{chat.title}</h5>
              <div className="d-flex gap-2">
                {useOrchestrator && currentSession && (
                  <Badge bg="success">Multi-Agent System</Badge>
                )}
                <Badge bg="info">Виртуальный экзаменатор</Badge>
              </div>
            </Card.Header>
            <Card.Body
              style={{
                height: 'calc(100vh - 250px)',
                overflowY: 'auto',
                backgroundColor: '#f8f9fa'
              }}
            >
              {error && (
                <Alert variant="danger" dismissible onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}
              {(chat.messages.length === 0 && (!useOrchestrator || dialogueHistory.length === 0)) ? (
                <div className="text-center text-muted py-5">
                  <h5>Начните экзамен</h5>
                  <p>Введите ответ на вопрос или задайте вопрос виртуальному экзаменатору</p>
                  {useOrchestrator && (
                    <p className="small text-info mt-2">
                      Используется мульти-агентная система для более точной оценки
                    </p>
                  )}
                </div>
              ) : (
                <div className="d-flex flex-column gap-3">
                  {/* Показываем историю диалога из оркестратора, если доступна */}
                  {useOrchestrator && dialogueHistory.length > 0 ? (
                    dialogueHistory.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`d-flex ${msg.sender === 'user' ? 'justify-content-end' : 'justify-content-start'}`}
                      >
                        <div
                          className={`p-3 rounded ${
                            msg.sender === 'user'
                              ? 'bg-primary text-white'
                              : 'bg-white border'
                          }`}
                          style={{ maxWidth: '70%' }}
                        >
                          <div>{msg.text}</div>
                          {msg.tactic && (
                            <Badge bg="secondary" className="mt-2" style={{ fontSize: '0.7rem' }}>
                              {msg.tactic}
                            </Badge>
                          )}
                          {msg.type && (
                            <Badge bg="info" className="mt-2 ms-1" style={{ fontSize: '0.7rem' }}>
                              {msg.type}
                            </Badge>
                          )}
                          <small
                            className={`d-block mt-2 ${
                              msg.sender === 'user' ? 'text-white-50' : 'text-muted'
                            }`}
                            style={{ fontSize: '0.75rem' }}
                          >
                            {new Date(msg.timestamp).toLocaleTimeString('ru-RU', {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </small>
                        </div>
                      </div>
                    ))
                  ) : (
                    chat.messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`d-flex ${msg.sender === 'user' ? 'justify-content-end' : 'justify-content-start'}`}
                      >
                        <div
                          className={`p-3 rounded ${
                            msg.sender === 'user'
                              ? 'bg-primary text-white'
                              : 'bg-white border'
                          }`}
                          style={{ maxWidth: '70%' }}
                        >
                          <div>{msg.text}</div>
                          <small
                            className={`d-block mt-2 ${
                              msg.sender === 'user' ? 'text-white-50' : 'text-muted'
                            }`}
                            style={{ fontSize: '0.75rem' }}
                          >
                            {new Date(msg.timestamp).toLocaleTimeString('ru-RU', {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </small>
                        </div>
                      </div>
                    ))
                  )}
                  {isLoading && (
                    <div className="d-flex justify-content-start">
                      <div className="bg-white border p-3 rounded">
                        <Spinner animation="border" size="sm" className="me-2" />
                        <span className="text-muted">Печатает...</span>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </Card.Body>
            <Card.Footer>
              <Form onSubmit={handleSend}>
                <InputGroup>
                  <Form.Control
                    type="text"
                    placeholder="Введите ответ или задайте вопрос..."
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    disabled={isLoading}
                  />
                  <Button
                    variant="primary"
                    type="submit"
                    disabled={!message.trim() || isLoading}
                  >
                    Отправить
                  </Button>
                </InputGroup>
              </Form>
            </Card.Footer>
          </Card>
        </Col>
      </Row>
    </Container>
  )
}

export default ChatDialog

