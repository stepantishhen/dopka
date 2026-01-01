import React from 'react'
import { Navbar, Nav, Container, Button, Badge } from 'react-bootstrap'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const Navigation = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, isTeacher, logout } = useAuth()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  if (!user) {
    return null
  }

  return (
    <Navbar bg="dark" variant="dark" expand="lg" className="mb-3">
      <Container>
        <Navbar.Brand as={Link} to="/">
          Система обучения
        </Navbar.Brand>
        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        <Navbar.Collapse id="basic-navbar-nav">
          <Nav className="me-auto">
            <Nav.Link as={Link} to="/" active={location.pathname === '/'}>
              Главная
            </Nav.Link>
            {isTeacher() && (
              <Nav.Link
                as={Link}
                to="/knowledge-base"
                active={location.pathname === '/knowledge-base'}
              >
                База знаний
              </Nav.Link>
            )}
            <Nav.Link as={Link} to="/history" active={location.pathname === '/history'}>
              История
            </Nav.Link>
            <Nav.Link as={Link} to="/profile" active={location.pathname === '/profile'}>
              Профиль
            </Nav.Link>
          </Nav>
          <Nav>
            <Navbar.Text className="me-3">
              <Badge bg={isTeacher() ? 'success' : 'primary'}>
                {isTeacher() ? 'Преподаватель' : 'Студент'}
              </Badge>
              {user.name && <span className="ms-2">{user.name}</span>}
            </Navbar.Text>
            <Button variant="outline-light" size="sm" onClick={handleLogout}>
              Выход
            </Button>
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  )
}

export default Navigation

