import React, { useState } from 'react'
import { Container, Card, Button, Form, Row, Col } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const Login = () => {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [name, setName] = useState('')

  const handleLogin = (role) => {
    login(role, name)
    navigate('/')
  }

  return (
    <Container className="py-5">
      <Row className="justify-content-center">
        <Col md={8} lg={6}>
          <Card>
            <Card.Header className="text-center">
              <h3>Система обучения</h3>
              <p className="text-muted mb-0">Выберите вашу роль</p>
            </Card.Header>
            <Card.Body>
              <Form.Group className="mb-4">
                <Form.Label>Ваше имя (необязательно)</Form.Label>
                <Form.Control
                  type="text"
                  placeholder="Введите ваше имя"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </Form.Group>

              <div className="d-grid gap-3">
                <Button
                  variant="primary"
                  size="lg"
                  onClick={() => handleLogin('student')}
                  className="py-3"
                >
                  <div className="d-flex flex-column align-items-center">
                    <strong>Я студент</strong>
                    <small className="mt-1">Общение с виртуальным экзаменатором</small>
                  </div>
                </Button>

                <Button
                  variant="success"
                  size="lg"
                  onClick={() => handleLogin('teacher')}
                  className="py-3"
                >
                  <div className="d-flex flex-column align-items-center">
                    <strong>Я преподаватель</strong>
                    <small className="mt-1">Управление базой знаний и просмотр истории</small>
                  </div>
                </Button>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  )
}

export default Login

