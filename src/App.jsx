import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Navigation from './components/Navigation'
import Login from './pages/Login'
import Home from './pages/Home'
import History from './pages/History'
import Profile from './pages/Profile'
import KnowledgeBase from './pages/KnowledgeBase'
import ChatDialog from './components/ChatDialog'
import ProtectedRoute from './components/ProtectedRoute'
import { ChatProvider } from './context/ChatContext'
import { AuthProvider } from './context/AuthContext'

function App() {
  return (
    <AuthProvider>
      <ChatProvider>
        <Router>
          <div className="d-flex flex-column" style={{ minHeight: '100vh' }}>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <Navigation />
                    <Routes>
                      <Route path="/" element={<Home />} />
                      <Route path="/chat/:chatId?" element={<ChatDialog />} />
                      <Route path="/history" element={<History />} />
                      <Route path="/profile" element={<Profile />} />
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
      </ChatProvider>
    </AuthProvider>
  )
}

export default App

