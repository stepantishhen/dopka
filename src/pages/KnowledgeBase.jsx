import React, { useState } from 'react'
import { Container, Card, Button, Form, Table, Modal, InputGroup, Badge, Alert } from 'react-bootstrap'
import { useChat } from '../context/ChatContext'

const KnowledgeBase = () => {
  const {
    knowledgeBase,
    addKnowledgeItem,
    updateKnowledgeItem,
    deleteKnowledgeItem,
    searchKnowledgeBase
  } = useChat()

  const [showModal, setShowModal] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    tags: '',
    category: ''
  })

  const filteredItems = searchTerm
    ? searchKnowledgeBase(searchTerm)
    : knowledgeBase

  const handleShowModal = (item = null) => {
    if (item) {
      setEditingItem(item)
      setFormData({
        title: item.title || '',
        content: item.content || '',
        tags: item.tags ? item.tags.join(', ') : '',
        category: item.category || ''
      })
    } else {
      setEditingItem(null)
      setFormData({
        title: '',
        content: '',
        tags: '',
        category: ''
      })
    }
    setShowModal(true)
  }

  const handleCloseModal = () => {
    setShowModal(false)
    setEditingItem(null)
    setFormData({
      title: '',
      content: '',
      tags: '',
      category: ''
    })
  }

  const handleSave = () => {
    const tagsArray = formData.tags
      .split(',')
      .map(tag => tag.trim())
      .filter(tag => tag.length > 0)

    if (editingItem) {
      updateKnowledgeItem(editingItem.id, {
        title: formData.title,
        content: formData.content,
        tags: tagsArray,
        category: formData.category
      })
    } else {
      addKnowledgeItem({
        title: formData.title,
        content: formData.content,
        tags: tagsArray,
        category: formData.category
      })
    }
    handleCloseModal()
  }

  const handleDelete = (id, title) => {
    if (window.confirm(`Вы уверены, что хотите удалить "${title}"?`)) {
      deleteKnowledgeItem(id)
    }
  }

  return (
    <Container className="py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>База знаний</h2>
        <Button variant="primary" onClick={() => handleShowModal()}>
          + Добавить материал
        </Button>
      </div>

      <InputGroup className="mb-4">
        <Form.Control
          type="text"
          placeholder="Поиск по названию, содержимому или тегам..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </InputGroup>

      {filteredItems.length === 0 ? (
        <Alert variant="info" className="text-center">
          {searchTerm
            ? 'Материалы не найдены'
            : 'База знаний пуста. Добавьте первый материал!'}
        </Alert>
      ) : (
        <Table striped bordered hover responsive>
          <thead>
            <tr>
              <th>Название</th>
              <th>Категория</th>
              <th>Теги</th>
              <th>Создан</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.map((item) => (
              <tr key={item.id}>
                <td>
                  <strong>{item.title}</strong>
                  {item.content && (
                    <div className="text-muted small mt-1" style={{
                      maxWidth: '300px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}>
                      {item.content}
                    </div>
                  )}
                </td>
                <td>
                  {item.category && (
                    <Badge bg="secondary">{item.category}</Badge>
                  )}
                </td>
                <td>
                  {item.tags && item.tags.length > 0 && (
                    <div>
                      {item.tags.map((tag, idx) => (
                        <Badge key={idx} bg="info" className="me-1">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                </td>
                <td>
                  {new Date(item.createdAt).toLocaleDateString('ru-RU')}
                </td>
                <td>
                  <Button
                    variant="outline-primary"
                    size="sm"
                    className="me-2"
                    onClick={() => handleShowModal(item)}
                  >
                    Редактировать
                  </Button>
                  <Button
                    variant="outline-danger"
                    size="sm"
                    onClick={() => handleDelete(item.id, item.title)}
                  >
                    Удалить
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal show={showModal} onHide={handleCloseModal} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>
            {editingItem ? 'Редактировать материал' : 'Добавить материал'}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label>Название *</Form.Label>
              <Form.Control
                type="text"
                value={formData.title}
                onChange={(e) =>
                  setFormData({ ...formData, title: e.target.value })
                }
                placeholder="Введите название материала"
                required
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Содержание *</Form.Label>
              <Form.Control
                as="textarea"
                rows={6}
                value={formData.content}
                onChange={(e) =>
                  setFormData({ ...formData, content: e.target.value })
                }
                placeholder="Введите содержание материала"
                required
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Категория</Form.Label>
              <Form.Control
                type="text"
                value={formData.category}
                onChange={(e) =>
                  setFormData({ ...formData, category: e.target.value })
                }
                placeholder="Например: Математика, Физика и т.д."
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Теги (через запятую)</Form.Label>
              <Form.Control
                type="text"
                value={formData.tags}
                onChange={(e) =>
                  setFormData({ ...formData, tags: e.target.value })
                }
                placeholder="тег1, тег2, тег3"
              />
              <Form.Text className="text-muted">
                Разделяйте теги запятыми
              </Form.Text>
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleCloseModal}>
            Отмена
          </Button>
          <Button
            variant="primary"
            onClick={handleSave}
            disabled={!formData.title || !formData.content}
          >
            Сохранить
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  )
}

export default KnowledgeBase

