import React, { useState, useEffect, useRef } from 'react'
import { Container, Row, Col, Card, Form, Button, InputGroup, Spinner, Badge } from 'react-bootstrap'
import { useParams, useNavigate } from 'react-router-dom'
import { useChat } from '../context/ChatContext'

const ChatDialog = () => {
  const { chatId } = useParams()
  const navigate = useNavigate()
  const { getChat, createChat, addMessage, updateChatTitle } = useChat()
  const [message, setMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const chat = chatId ? getChat(chatId) : null

  useEffect(() => {
    if (!chatId) {
      const newChatId = createChat()
      navigate(`/chat/${newChatId}`, { replace: true })
    }
  }, [chatId, createChat, navigate])

  useEffect(() => {
    scrollToBottom()
  }, [chat?.messages])

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

    // Симуляция ответа от AI
    setTimeout(() => {
      const aiMessage = {
        id: (Date.now() + 1).toString(),
        text: generateAIResponse(message),
        sender: 'ai',
        timestamp: new Date().toISOString()
      }
      addMessage(chat.id, aiMessage)
      
      // Обновляем заголовок чата, если это первый обмен сообщениями
      if (chat.messages.length === 0) {
        const title = message.length > 30 ? message.substring(0, 30) + '...' : message
        updateChatTitle(chat.id, title)
      }
      
      setIsLoading(false)
    }, 1000 + Math.random() * 1000)
  }

  const generateAIResponse = (userMessage) => {
    // Симуляция ответа виртуального экзаменатора
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
              <Badge bg="info">Виртуальный экзаменатор</Badge>
            </Card.Header>
            <Card.Body
              style={{
                height: 'calc(100vh - 250px)',
                overflowY: 'auto',
                backgroundColor: '#f8f9fa'
              }}
            >
              {chat.messages.length === 0 ? (
                <div className="text-center text-muted py-5">
                  <h5>Начните экзамен</h5>
                  <p>Введите ответ на вопрос или задайте вопрос виртуальному экзаменатору</p>
                </div>
              ) : (
                <div className="d-flex flex-column gap-3">
                  {chat.messages.map((msg) => (
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
                  ))}
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

