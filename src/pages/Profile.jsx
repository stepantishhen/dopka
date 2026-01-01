import React, { useState } from 'react'
import { Container, Card, Form, Button, Row, Col, Badge, Alert } from 'react-bootstrap'
import { useChat } from '../context/ChatContext'
import { useAuth } from '../context/AuthContext'

const Profile = () => {
  const { chats, knowledgeBase } = useChat()
  const { user, isTeacher } = useAuth()
  const [profile, setProfile] = useState(() => {
    const saved = localStorage.getItem('profile')
    return saved ? JSON.parse(saved) : {
      name: '',
      email: '',
      bio: ''
    }
  })

  const handleChange = (e) => {
    const { name, value } = e.target
    setProfile(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSave = () => {
    localStorage.setItem('profile', JSON.stringify(profile))
    alert('Профиль сохранен!')
  }

  const totalMessages = chats.reduce((sum, chat) => sum + chat.messages.length, 0)
  const totalChats = chats.length

  return (
    <Container className="py-4">
      <Row>
        <Col md={8}>
          <Card className="mb-4">
            <Card.Header>
              <h4 className="mb-0">
                Настройки профиля
                <Badge bg={isTeacher() ? 'success' : 'primary'} className="ms-2">
                  {isTeacher() ? 'Преподаватель' : 'Студент'}
                </Badge>
              </h4>
            </Card.Header>
            <Card.Body>
              <Form>
                <Form.Group className="mb-3">
                  <Form.Label>Имя</Form.Label>
                  <Form.Control
                    type="text"
                    name="name"
                    value={profile.name}
                    onChange={handleChange}
                    placeholder="Введите ваше имя"
                  />
                </Form.Group>

                <Form.Group className="mb-3">
                  <Form.Label>Email</Form.Label>
                  <Form.Control
                    type="email"
                    name="email"
                    value={profile.email}
                    onChange={handleChange}
                    placeholder="Введите ваш email"
                  />
                </Form.Group>

                <Form.Group className="mb-3">
                  <Form.Label>О себе</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={4}
                    name="bio"
                    value={profile.bio}
                    onChange={handleChange}
                    placeholder="Расскажите о себе"
                  />
                </Form.Group>

                <Button variant="primary" onClick={handleSave}>
                  Сохранить изменения
                </Button>
              </Form>
            </Card.Body>
          </Card>
        </Col>

        <Col md={4}>
          <Card>
            <Card.Header>
              <h5 className="mb-0">Статистика</h5>
            </Card.Header>
            <Card.Body>
              <div className="mb-3">
                {isTeacher() ? (
                  <>
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <span>Материалов в базе знаний:</span>
                      <Badge bg="primary">{knowledgeBase.length}</Badge>
                    </div>
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <span>Всего диалогов студентов:</span>
                      <Badge bg="info">{totalChats}</Badge>
                    </div>
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <span>Всего сообщений:</span>
                      <Badge bg="success">{totalMessages}</Badge>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <span>Пройдено экзаменов:</span>
                      <Badge bg="primary">{totalChats}</Badge>
                    </div>
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <span>Всего сообщений:</span>
                      <Badge bg="success">{totalMessages}</Badge>
                    </div>
                    <div className="d-flex justify-content-between align-items-center">
                      <span>Среднее на экзамен:</span>
                      <Badge bg="info">
                        {totalChats > 0 ? Math.round(totalMessages / totalChats) : 0}
                      </Badge>
                    </div>
                  </>
                )}
              </div>
            </Card.Body>
          </Card>

          <Card className="mt-3">
            <Card.Header>
              <h5 className="mb-0">Информация</h5>
            </Card.Header>
            <Card.Body>
              <Alert variant="info" className="mb-0">
                <small>
                  Ваши данные хранятся локально в браузере. 
                  Для синхронизации между устройствами необходима интеграция с backend.
                </small>
              </Alert>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  )
}

export default Profile

