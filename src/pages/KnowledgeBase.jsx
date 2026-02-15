import React, { useState } from 'react'
import { Container, Card, Button, Form, Table, Modal, InputGroup, Badge, Alert, Spinner } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import { useChat } from '../context/ChatContext'
import api from '../services/api'

const KnowledgeBase = () => {
  const navigate = useNavigate()
  const {
    knowledgeBase,
    addKnowledgeItem,
    updateKnowledgeItem,
    deleteKnowledgeItem,
    searchKnowledgeBase
  } = useChat()

  const [showModal, setShowModal] = useState(false)
  const [showCreateExamModal, setShowCreateExamModal] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    tags: '',
    category: ''
  })
  const [examFormData, setExamFormData] = useState({
    name: '',
    text: '',
    numQuestions: 10,
    adaptive: true
  })
  const [selectedFile, setSelectedFile] = useState(null)
  const [isCreatingExam, setIsCreatingExam] = useState(false)
  const [examCreationError, setExamCreationError] = useState(null)
  const [examCreationSuccess, setExamCreationSuccess] = useState(null)
  const [activeTab, setActiveTab] = useState('text')

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

  const handleCreateExamFromText = async () => {
    if (!examFormData.name || !examFormData.text) {
      setExamCreationError('Заполните название и текст материала')
      return
    }

    setIsCreatingExam(true)
    setExamCreationError(null)
    setExamCreationSuccess(null)

    try {
      const exam = await api.createExamFromMaterials(
        examFormData.name,
        examFormData.text,
        null,
        examFormData.numQuestions,
        examFormData.adaptive
      )

      setExamCreationSuccess(`Экзамен "${exam.config.name}" успешно создан! ID: ${exam.exam_id}`)
      
      setTimeout(() => {
        setShowCreateExamModal(false)
        setExamFormData({ name: '', text: '', numQuestions: 10, adaptive: true })
        setExamCreationSuccess(null)

        alert(`Экзамен создан! Студенты могут начать его прохождение.`)
      }, 2000)
    } catch (error) {
      setExamCreationError(error.message || 'Ошибка при создании экзамена')
    } finally {
      setIsCreatingExam(false)
    }
  }

  const handleCreateExamFromPDF = async () => {
    if (!examFormData.name || !selectedFile) {
      setExamCreationError('Заполните название и выберите PDF файл')
      return
    }

    setIsCreatingExam(true)
    setExamCreationError(null)
    setExamCreationSuccess(null)

    try {
      const exam = await api.createExamFromPDF(
        selectedFile,
        examFormData.name,
        examFormData.numQuestions,
        examFormData.adaptive
      )

      setExamCreationSuccess(`Экзамен "${exam.config.name}" успешно создан! ID: ${exam.exam_id}`)
      

      setTimeout(() => {
        setShowCreateExamModal(false)
        setExamFormData({ name: '', text: '', numQuestions: 10, adaptive: true })
        setSelectedFile(null)
        setExamCreationSuccess(null)

        if (window.confirm(`Экзамен "${exam.config.name}" успешно создан! Перейти к списку экзаменов?`)) {
          navigate('/exams')
        }
      }, 2000)
    } catch (error) {
      setExamCreationError(error.message || 'Ошибка при создании экзамена')
    } finally {
      setIsCreatingExam(false)
    }
  }

  const handleFileChange = (e) => {
    const file = e.target.files[0]
    if (file) {
      if (file.type !== 'application/pdf') {
        setExamCreationError('Пожалуйста, выберите PDF файл')
        return
      }
      setSelectedFile(file)
      if (!examFormData.name) {
        setExamFormData({ ...examFormData, name: file.name.replace('.pdf', '') })
      }
    }
  }

  return (
    <Container className="py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>База знаний</h2>
        <div className="d-flex gap-2">
          <Button variant="success" onClick={() => setShowCreateExamModal(true)}>
            📝 Создать экзамен из материалов
          </Button>
          <Button variant="primary" onClick={() => handleShowModal()}>
            + Добавить материал
          </Button>
        </div>
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

      <Modal show={showCreateExamModal} onHide={() => setShowCreateExamModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Создать экзамен из материалов</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {examCreationError && (
            <Alert variant="danger" dismissible onClose={() => setExamCreationError(null)}>
              {examCreationError}
            </Alert>
          )}
          {examCreationSuccess && (
            <Alert variant="success">
              {examCreationSuccess}
            </Alert>
          )}

          <div className="mb-3">
            <Button
              variant={activeTab === 'text' ? 'primary' : 'outline-primary'}
              className="me-2"
              onClick={() => setActiveTab('text')}
            >
              Из текста
            </Button>
            <Button
              variant={activeTab === 'pdf' ? 'primary' : 'outline-primary'}
              onClick={() => setActiveTab('pdf')}
            >
              Из PDF
            </Button>
          </div>

          {activeTab === 'text' && (
            <div>
              <Form>
                <Form.Group className="mb-3">
                  <Form.Label>Название экзамена *</Form.Label>
                  <Form.Control
                    type="text"
                    value={examFormData.name}
                    onChange={(e) =>
                      setExamFormData({ ...examFormData, name: e.target.value })
                    }
                    placeholder="Например: Экзамен по Python"
                    required
                  />
                </Form.Group>

                <Form.Group className="mb-3">
                  <Form.Label>Текст материала *</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={10}
                    value={examFormData.text}
                    onChange={(e) =>
                      setExamFormData({ ...examFormData, text: e.target.value })
                    }
                    placeholder="Вставьте текст учебного материала. Система автоматически извлечет знания и создаст вопросы."
                    required
                  />
                  <Form.Text className="text-muted">
                    Система автоматически извлечет дидактические единицы и сгенерирует вопросы
                  </Form.Text>
                </Form.Group>

                <Form.Group className="mb-3">
                  <Form.Label>Количество вопросов</Form.Label>
                  <Form.Control
                    type="number"
                    min="5"
                    max="50"
                    value={examFormData.numQuestions}
                    onChange={(e) =>
                      setExamFormData({ ...examFormData, numQuestions: parseInt(e.target.value) })
                    }
                  />
                </Form.Group>

                <Form.Check
                  type="checkbox"
                  label="Адаптивный экзамен"
                  checked={examFormData.adaptive}
                  onChange={(e) =>
                    setExamFormData({ ...examFormData, adaptive: e.target.checked })
                  }
                  className="mb-3"
                />
              </Form>
            </div>
          )}

          {activeTab === 'pdf' && (
            <div>
              <Form>
                <Form.Group className="mb-3">
                  <Form.Label>Название экзамена *</Form.Label>
                  <Form.Control
                    type="text"
                    value={examFormData.name}
                    onChange={(e) =>
                      setExamFormData({ ...examFormData, name: e.target.value })
                    }
                    placeholder="Например: Экзамен по Python"
                    required
                  />
                </Form.Group>

                <Form.Group className="mb-3">
                  <Form.Label>PDF файл *</Form.Label>
                  <Form.Control
                    type="file"
                    accept=".pdf"
                    onChange={handleFileChange}
                    required
                  />
                  <Form.Text className="text-muted">
                    Загрузите PDF файл с учебным материалом. Система извлечет текст и создаст экзамен.
                  </Form.Text>
                  {selectedFile && (
                    <Alert variant="info" className="mt-2">
                      Выбран файл: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(2)} KB)
                    </Alert>
                  )}
                </Form.Group>

                <Form.Group className="mb-3">
                  <Form.Label>Количество вопросов</Form.Label>
                  <Form.Control
                    type="number"
                    min="5"
                    max="50"
                    value={examFormData.numQuestions}
                    onChange={(e) =>
                      setExamFormData({ ...examFormData, numQuestions: parseInt(e.target.value) })
                    }
                  />
                </Form.Group>

                <Form.Check
                  type="checkbox"
                  label="Адаптивный экзамен"
                  checked={examFormData.adaptive}
                  onChange={(e) =>
                    setExamFormData({ ...examFormData, adaptive: e.target.checked })
                  }
                  className="mb-3"
                />
              </Form>
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowCreateExamModal(false)}>
            Отмена
          </Button>
          <Button
            variant="success"
            onClick={selectedFile ? handleCreateExamFromPDF : handleCreateExamFromText}
            disabled={isCreatingExam || (!examFormData.name || (!examFormData.text && !selectedFile))}
          >
            {isCreatingExam ? (
              <>
                <Spinner animation="border" size="sm" className="me-2" />
                Создание экзамена...
              </>
            ) : (
              'Создать экзамен'
            )}
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  )
}

export default KnowledgeBase

