import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useParams } from 'react-router-dom'
import Navigation from './components/Navigation'
import Login from './pages/Login'
import JoinExam from './pages/JoinExam'
import Home from './pages/Home'
import History from './pages/History'
import Profile from './pages/Profile'
import KnowledgeBase from './pages/KnowledgeBase'
import Exams from './pages/Exams'
import ChatDialog from './components/ChatDialog'
import ExamSession from './components/ExamSession'
import Analytics from './components/Analytics'
import ProtectedRoute from './components/ProtectedRoute'
import { ChatProvider } from './context/ChatContext'
import { AuthProvider } from './context/AuthContext'
import { ExamSessionProvider } from './context/ExamSessionContext'

const ExamSessionWrapper = () => {
  const { examId } = useParams()
  return <ExamSession examId={examId} />
}

function App() {
  return (
    <AuthProvider>
      <ChatProvider>
        <ExamSessionProvider>
          <Router>
          <div className="d-flex flex-column" style={{ minHeight: '100vh' }}>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/join/:code?" element={<JoinExam />} />
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <Navigation />
                    <Routes>
                      <Route path="/" element={<Home />} />
                      <Route path="/chat/:chatId?" element={<ChatDialog />} />
                      <Route path="/exam/:examId?" element={<ExamSessionWrapper />} />
                      <Route path="/history" element={<History />} />
                      <Route path="/profile" element={<Profile />} />
                      <Route path="/analytics" element={<Analytics />} />
                      <Route
                        path="/exams"
                        element={
                          <ProtectedRoute requireTeacher>
                            <Exams />
                          </ProtectedRoute>
                        }
                      />
                      <Route
                        path="/knowledge-base"
                        element={
                          <ProtectedRoute requireTeacher>
                            <KnowledgeBase />
                          </ProtectedRoute>
                        }
                      />
                      <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                  </ProtectedRoute>
                }
              />
            </Routes>
          </div>
        </Router>
        </ExamSessionProvider>
      </ChatProvider>
    </AuthProvider>
  )
}

export default App

