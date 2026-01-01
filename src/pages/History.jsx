import React, { useState } from 'react'
import { Container, Table, Button, InputGroup, Form, Badge } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import { useChat } from '../context/ChatContext'

const History = () => {
  const navigate = useNavigate()
  const { chats, deleteChat } = useChat()
  const [searchTerm, setSearchTerm] = useState('')

  const filteredChats = chats.filter(chat =>
    chat.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    chat.messages.some(msg => msg.text.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  const handleChatClick = (chatId) => {
    navigate(`/chat/${chatId}`)
  }

  const handleDelete = (chatId, title) => {
    if (window.confirm(`Вы уверены, что хотите удалить диалог "${title}"?`)) {
      deleteChat(chatId)
    }
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleString('ru-RU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <Container className="py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>История диалогов</h2>
        <Badge bg="secondary">{chats.length} диалогов</Badge>
      </div>

      <InputGroup className="mb-4">
        <Form.Control
          type="text"
          placeholder="Поиск по названию или содержимому..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </InputGroup>

      {filteredChats.length === 0 ? (
        <div className="text-center py-5">
          <p className="text-muted">
            {searchTerm ? 'Диалоги не найдены' : 'История диалогов пуста'}
          </p>
        </div>
      ) : (
        <Table striped bordered hover responsive>
          <thead>
            <tr>
              <th>Название</th>
              <th>Сообщений</th>
              <th>Создан</th>
              <th>Обновлен</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {filteredChats.map((chat) => (
              <tr key={chat.id}>
                <td>
                  <Button
                    variant="link"
                    className="p-0 text-start text-decoration-none"
                    onClick={() => handleChatClick(chat.id)}
                  >
                    {chat.title}
                  </Button>
                </td>
                <td>
                  <Badge bg="info">{chat.messages.length}</Badge>
                </td>
                <td>{formatDate(chat.createdAt)}</td>
                <td>{formatDate(chat.updatedAt)}</td>
                <td>
                  <Button
                    variant="outline-primary"
                    size="sm"
                    className="me-2"
                    onClick={() => handleChatClick(chat.id)}
                  >
                    Открыть
                  </Button>
                  <Button
                    variant="outline-danger"
                    size="sm"
                    onClick={() => handleDelete(chat.id, chat.title)}
                  >
                    Удалить
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </Container>
  )
}

export default History

