import React, { useState } from 'react'
import { Container, Card, Button, Form, Row, Col, Tabs, Tab } from 'react-bootstrap'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

const Login = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const redirect = searchParams.get('redirect') || '/'
  const joinCode = searchParams.get('join')
  const { login, loginWithCredentials } = useAuth()
  
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [role, setRole] = useState('student')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.login(email, password)
      loginWithCredentials(res)
      navigate(joinCode ? `/join/${joinCode}` : redirect)
    } catch (err) {
      setError(err.message || 'Ошибка входа')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setError('')
    if (password.length < 6) {
      setError('Пароль должен быть не менее 6 символов')
      return
    }
    setLoading(true)
    try {
      const res = await api.register(email, password, name, role)
      loginWithCredentials(res)
      navigate(joinCode ? `/join/${joinCode}` : redirect)
    } catch (err) {
      setError(err.message || 'Ошибка регистрации')
    } finally {
      setLoading(false)
    }
  }

  const handleQuickLogin = (r) => {
    login(r, name)
    navigate(joinCode ? `/join/${joinCode}` : redirect)
  }

  return (
    <Container className="py-5">
      <Row className="justify-content-center">
        <Col md={8} lg={6}>
          <Card>
            <Card.Header className="text-center">
              <h3>Система обучения</h3>
              <p className="text-muted mb-0">
                {joinCode ? `Присоединиться к экзамену (код: ${joinCode})` : 'Войдите или зарегистрируйтесь'}
              </p>
            </Card.Header>
            <Card.Body>
              <Tabs activeKey={mode} onSelect={(k) => { setMode(k); setError('') }} className="mb-4">
                <Tab eventKey="login" title="Вход">
                  <Form onSubmit={handleLogin}>
                    <Form.Group className="mb-3">
                      <Form.Label>Email</Form.Label>
                      <Form.Control
                        type="email"
                        placeholder="email@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                      />
                    </Form.Group>
                    <Form.Group className="mb-3">
                      <Form.Label>Пароль</Form.Label>
                      <Form.Control
                        type="password"
                        placeholder="Пароль"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                      />
                    </Form.Group>
                    {error && <div className="text-danger mb-2">{error}</div>}
                    <Button variant="primary" type="submit" className="w-100" disabled={loading}>
                      {loading ? 'Вход...' : 'Войти'}
                    </Button>
                  </Form>
                </Tab>
                <Tab eventKey="register" title="Регистрация">
                  <Form onSubmit={handleRegister}>
                    <Form.Group className="mb-3">
                      <Form.Label>Email</Form.Label>
                      <Form.Control
                        type="email"
                        placeholder="email@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                      />
                    </Form.Group>
                    <Form.Group className="mb-3">
                      <Form.Label>Пароль (мин. 6 символов)</Form.Label>
                      <Form.Control
                        type="password"
                        placeholder="Пароль"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                      />
                    </Form.Group>
                    <Form.Group className="mb-3">
                      <Form.Label>Имя</Form.Label>
                      <Form.Control
                        type="text"
                        placeholder="Ваше имя"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        required
                      />
                    </Form.Group>
                    <Form.Group className="mb-3">
                      <Form.Label>Роль</Form.Label>
                      <Form.Select value={role} onChange={(e) => setRole(e.target.value)}>
                        <option value="student">Студент</option>
                        <option value="teacher">Преподаватель</option>
                      </Form.Select>
                    </Form.Group>
                    {error && <div className="text-danger mb-2">{error}</div>}
                    <Button variant="success" type="submit" className="w-100" disabled={loading}>
                      {loading ? 'Регистрация...' : 'Зарегистрироваться'}
                    </Button>
                  </Form>
                </Tab>
              </Tabs>
              
              <hr />
              <p className="text-muted text-center mb-2 small">Быстрый вход (без регистрации)</p>
              <div className="d-grid gap-2">
                <Button variant="outline-primary" onClick={() => handleQuickLogin('student')}>
                  Я студент
                </Button>
                <Button variant="outline-success" onClick={() => handleQuickLogin('teacher')}>
                  Я преподаватель
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
