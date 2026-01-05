import React, { useState, useEffect } from 'react'
import { Container, Row, Col, Card, Spinner, Alert } from 'react-bootstrap'
import api from '../services/api'

const Analytics = () => {
  const [metrics, setMetrics] = useState(null)
  const [insights, setInsights] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadMetrics()
  }, [])

  const loadMetrics = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await api.getMetrics()
      setMetrics(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <Container className="py-4">
        <div className="text-center">
          <Spinner animation="border" />
        </div>
      </Container>
    )
  }

  if (error) {
    return (
      <Container className="py-4">
        <Alert variant="danger">{error}</Alert>
      </Container>
    )
  }

  return (
    <Container className="py-4">
      <h2 className="mb-4">Аналитика системы</h2>

      {metrics && (
        <Row className="mb-4">
          <Col md={4}>
            <Card>
              <Card.Header>API Запросы</Card.Header>
              <Card.Body>
                <h5>{metrics.api_requests?.total || 0}</h5>
                <p className="text-muted mb-0">
                  Среднее время ответа:{' '}
                  {metrics.api_requests?.avg_response_time_ms
                    ? `${metrics.api_requests.avg_response_time_ms.toFixed(2)} мс`
                    : 'N/A'}
                </p>
                {metrics.api_requests?.status_codes && (
                  <div className="mt-2">
                    {Object.entries(metrics.api_requests.status_codes).map(([code, count]) => (
                      <span key={code} className="badge bg-secondary me-1">
                        {code}: {count}
                      </span>
                    ))}
                  </div>
                )}
              </Card.Body>
            </Card>
          </Col>

          <Col md={4}>
            <Card>
              <Card.Header>Вызовы агентов</Card.Header>
              <Card.Body>
                <h5>{metrics.agent_calls?.total || 0}</h5>
                {metrics.agent_calls?.by_agent && (
                  <div className="mt-2">
                    {Object.entries(metrics.agent_calls.by_agent).map(([agent, stats]) => (
                      <div key={agent} className="mb-2">
                        <strong>{agent}:</strong> Всего: {stats.total}, Успешно:{' '}
                        {stats.success}, Ошибок: {stats.failed}
                      </div>
                    ))}
                  </div>
                )}
              </Card.Body>
            </Card>
          </Col>

          <Col md={4}>
            <Card>
              <Card.Header>Ошибки</Card.Header>
              <Card.Body>
                <h5>{metrics.errors?.total || 0}</h5>
                {metrics.errors?.recent && metrics.errors.recent.length > 0 && (
                  <div className="mt-2">
                    <strong>Последние ошибки:</strong>
                    <ul className="mt-2">
                      {metrics.errors.recent.slice(0, 5).map((err, idx) => (
                        <li key={idx} style={{ fontSize: '0.9rem' }}>
                          [{err.error_type}] {err.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}

      {insights && (
        <Row>
          <Col>
            <Card>
              <Card.Header>Инсайты</Card.Header>
              <Card.Body>
                {insights.insights?.key_insights && (
                  <div className="mb-3">
                    <h6>Ключевые инсайты:</h6>
                    <ul>
                      {insights.insights.key_insights.map((insight, idx) => (
                        <li key={idx}>{insight}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {insights.insights?.recommendations && (
                  <div>
                    <h6>Рекомендации:</h6>
                    <ul>
                      {insights.insights.recommendations.map((rec, idx) => (
                        <li key={idx}>{rec}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}
    </Container>
  )
}

export default Analytics

