import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const ProtectedRoute = ({ children, requireTeacher = false }) => {
  const { user, isStaff } = useAuth()

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (requireTeacher && !isStaff()) {
    return <Navigate to="/" replace />
  }

  return children
}

export default ProtectedRoute

