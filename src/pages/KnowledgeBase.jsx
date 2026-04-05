import React, { useState, useEffect, useCallback } from 'react'
import { Container, Card, Button, Form, Table, Modal, InputGroup, Badge, Alert, Spinner } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'

const KnowledgeBase = () => {
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [listError, setListError] = useState(null)

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
  const [importBusy, setImportBusy] = useState(false)
  const [lastExamLinks, setLastExamLinks] = useState(null)

  const copyText = (text) => {
    if (!text) return
    navigator.clipboard?.writeText(text).catch(() => {})
  }

  const loadItems = useCallback(async () => {
    try {
      setLoading(true)
      setListError(null)
      const data = await api.getKnowledgeItems()
      setItems(Array.isArray(data) ? data : [])
    } catch (e) {
      setListError(e.message || 'Не удалось загрузить базу знаний')
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadItems()
  }, [loadItems])

  const filteredItems = searchTerm
    ? items.filter((item) => {
        const q = searchTerm.toLowerCase()
        return (
          (item.title && item.title.toLowerCase().includes(q)) ||
          (item.content && item.content.toLowerCase().includes(q)) ||
          (item.tags && item.tags.some((t) => t.toLowerCase().includes(q)))
        )
      })
    : items

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

  const handleSave = async () => {
    const tagsArray = formData.tags
      .split(',')
      .map(tag => tag.trim())
      .filter(tag => tag.length > 0)

    try {
      if (editingItem) {
        await api.updateKnowledgeItem(editingItem.id, {
          title: formData.title,
          content: formData.content,
          tags: tagsArray,
          category: formData.category
        })
      } else {
        await api.createKnowledgeItem({
          title: formData.title,
          content: formData.content,
          tags: tagsArray,
          category: formData.category
        })
      }
      await loadItems()
      handleCloseModal()
    } catch (e) {
      alert(e.message || 'Ошибка сохранения')
    }
  }

  const handleDelete = async (id, title) => {
    if (!window.confirm(`Вы уверены, что хотите удалить "${title}"?`)) return
    try {
      await api.deleteKnowledgeItem(id)
      await loadItems()
    } catch (e) {
      alert(e.message || 'Ошибка удаления')
    }
  }

  const handleImportToKbPdf = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImportBusy(true)
    try {
      await api.extractFromPDF(file)
      await loadItems()
      alert('Материалы из PDF добавлены в базу знаний.')
    } catch (err) {
      alert(err.message || 'Ошибка импорта PDF')
    } finally {
      setImportBusy(false)
      e.target.value = ''
    }
  }

  const handleImportToKbDocx = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImportBusy(true)
    try {
      await api.extractFromDOCX(file)
      await loadItems()
      alert('Материалы из DOCX добавлены в базу знаний.')
    } catch (err) {
      alert(err.message || 'Ошибка импорта DOCX')
    } finally {
      setImportBusy(false)
      e.target.value = ''
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

      const origin = typeof window !== 'undefined' ? window.location.origin : ''
      setLastExamLinks({
        name: exam.config?.name,
        examId: exam.exam_id,
        joinCode: exam.join_code,
        joinUrl: exam.join_path ? `${origin}${exam.join_path}` : '',
        examUrl: exam.exam_path ? `${origin}${exam.exam_path}` : '',
      })
      setExamCreationSuccess(`Экзамен «${exam.config.name}» создан. Скопируйте ссылку для студентов ниже.`)
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

      const origin = typeof window !== 'undefined' ? window.location.origin : ''
      setLastExamLinks({
        name: exam.config?.name,
        examId: exam.exam_id,
        joinCode: exam.join_code,
        joinUrl: exam.join_path ? `${origin}${exam.join_path}` : '',
        examUrl: exam.exam_path ? `${origin}${exam.exam_path}` : '',
      })
      setExamCreationSuccess(`Экзамен «${exam.config.name}» создан. Скопируйте ссылку для студентов ниже.`)
    } catch (error) {
      setExamCreationError(error.message || 'Ошибка при создании экзамена')
    } finally {
      setIsCreatingExam(false)
    }
  }

  const handleCreateExamFromDOCX = async () => {
    if (!examFormData.name || !selectedFile) {
      setExamCreationError('Заполните название и выберите DOCX файл')
      return
    }

    setIsCreatingExam(true)
    setExamCreationError(null)
    setExamCreationSuccess(null)

    try {
      const exam = await api.createExamFromDOCX(
        selectedFile,
        examFormData.name,
        examFormData.numQuestions,
        examFormData.adaptive
      )

      const origin = typeof window !== 'undefined' ? window.location.origin : ''
      setLastExamLinks({
        name: exam.config?.name,
        examId: exam.exam_id,
        joinCode: exam.join_code,
        joinUrl: exam.join_path ? `${origin}${exam.join_path}` : '',
        examUrl: exam.exam_path ? `${origin}${exam.exam_path}` : '',
      })
      setExamCreationSuccess(`Экзамен «${exam.config.name}» создан. Скопируйте ссылку для студентов ниже.`)
    } catch (error) {
      setExamCreationError(error.message || 'Ошибка при создании экзамена')
    } finally {
      setIsCreatingExam(false)
    }
  }

  const handleFileChange = (e) => {
    const file = e.target.files[0]
    if (file) {
      const okPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
      const okDocx =
        file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
        file.name.toLowerCase().endsWith('.docx')
      if (activeTab === 'pdf' && !okPdf) {
        setExamCreationError('Пожалуйста, выберите PDF файл')
        return
      }
      if (activeTab === 'docx' && !okDocx) {
        setExamCreationError('Пожалуйста, выберите DOCX файл')
        return
      }
      setSelectedFile(file)
      if (!examFormData.name) {
        const base = file.name.replace(/\.(pdf|docx)$/i, '')
        setExamFormData({ ...examFormData, name: base })
      }
    }
  }

  return (
    <Container className="py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>База знаний</h2>
        <div className="d-flex gap-2 flex-wrap">
          <Button variant="success" onClick={() => setShowCreateExamModal(true)}>
            📝 Создать экзамен из материалов
          </Button>
          <Button variant="primary" onClick={() => handleShowModal()}>
            + Добавить материал
          </Button>
        </div>
      </div>

      <Card className="mb-4">
        <Card.Body>
          <Card.Title as="h6">Импорт в базу знаний (PDF / DOCX)</Card.Title>
          <p className="text-muted small mb-2">
            Текст извлекается на сервере; дидактические единицы добавляются в базу через LLM.
          </p>
          <div className="d-flex flex-wrap gap-2 align-items-center">
            <Form.Control
              type="file"
              accept=".pdf,application/pdf"
              disabled={importBusy}
              onChange={handleImportToKbPdf}
              style={{ maxWidth: 280 }}
            />
            <Form.Control
              type="file"
              accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              disabled={importBusy}
              onChange={handleImportToKbDocx}
              style={{ maxWidth: 280 }}
            />
            {importBusy && <Spinner animation="border" size="sm" />}
          </div>
        </Card.Body>
      </Card>

      {listError && (
        <Alert variant="warning" className="mb-3">
          {listError}
        </Alert>
      )}

      <InputGroup className="mb-4">
        <Form.Control
          type="text"
          placeholder="Поиск по названию, содержимому или тегам..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </InputGroup>

      {loading ? (
        <div className="text-center py-5">
          <Spinner animation="border" />
        </div>
      ) : filteredItems.length === 0 ? (
        <Alert variant="info" className="text-center">
          {searchTerm
            ? 'Материалы не найдены'
            : 'База знаний пуста. Добавьте первый материал или импортируйте PDF/DOCX.'}
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

      <Modal
        show={showCreateExamModal}
        onHide={() => {
          setShowCreateExamModal(false)
          setLastExamLinks(null)
          setExamCreationSuccess(null)
          setExamCreationError(null)
        }}
        size="lg"
      >
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
          {lastExamLinks && (
            <Alert variant="info" className="small">
              <div className="fw-semibold mb-2">Для студентов</div>
              <div className="mb-1">
                Код: <code>{lastExamLinks.joinCode}</code>
              </div>
              {lastExamLinks.joinUrl && (
                <div className="d-flex flex-wrap align-items-center gap-2 mb-1">
                  <span className="text-break">{lastExamLinks.joinUrl}</span>
                  <Button size="sm" variant="outline-primary" onClick={() => copyText(lastExamLinks.joinUrl)}>
                    Копировать ссылку
                  </Button>
                </div>
              )}
              {lastExamLinks.examUrl && (
                <div className="d-flex flex-wrap align-items-center gap-2 mt-2">
                  <span className="text-muted">Прямая ссылка на экран экзамена (после входа):</span>
                  <Button size="sm" variant="outline-secondary" onClick={() => copyText(lastExamLinks.examUrl)}>
                    Копировать
                  </Button>
                </div>
              )}
              <div className="mt-2">
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => {
                    setShowCreateExamModal(false)
                    setLastExamLinks(null)
                    navigate('/exams')
                  }}
                >
                  К списку экзаменов
                </Button>
              </div>
            </Alert>
          )}

          <div className="mb-3">
            <Button
              variant={activeTab === 'text' ? 'primary' : 'outline-primary'}
              className="me-2"
              onClick={() => {
                setActiveTab('text')
                setSelectedFile(null)
              }}
            >
              Из текста
            </Button>
            <Button
              variant={activeTab === 'pdf' ? 'primary' : 'outline-primary'}
              onClick={() => {
                setActiveTab('pdf')
                setSelectedFile(null)
              }}
            >
              Из PDF
            </Button>
            <Button
              variant={activeTab === 'docx' ? 'primary' : 'outline-primary'}
              className="ms-2"
              onClick={() => {
                setActiveTab('docx')
                setSelectedFile(null)
              }}
            >
              Из DOCX
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

          {(activeTab === 'pdf' || activeTab === 'docx') && (
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
                  <Form.Label>{activeTab === 'pdf' ? 'PDF' : 'DOCX'} файл *</Form.Label>
                  <Form.Control
                    type="file"
                    accept={activeTab === 'pdf' ? '.pdf' : '.docx'}
                    onChange={handleFileChange}
                    required
                  />
                  <Form.Text className="text-muted">
                    {activeTab === 'pdf'
                      ? 'Загрузите PDF: текст извлекается на сервере, затем формируется экзамен.'
                      : 'Загрузите DOCX: текст извлекается на сервере, затем формируется экзамен.'}
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
            onClick={
              activeTab === 'text'
                ? handleCreateExamFromText
                : activeTab === 'pdf'
                  ? handleCreateExamFromPDF
                  : handleCreateExamFromDOCX
            }
            disabled={
              isCreatingExam ||
              !examFormData.name ||
              (activeTab === 'text' && !examFormData.text) ||
              ((activeTab === 'pdf' || activeTab === 'docx') && !selectedFile)
            }
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

