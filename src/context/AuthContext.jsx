import React, { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user')
    return saved ? JSON.parse(saved) : null
  })
  const [token, setToken] = useState(() => localStorage.getItem('token') || null)

  useEffect(() => {
    if (user && token) {
      localStorage.setItem('user', JSON.stringify(user))
      localStorage.setItem('token', token)
    } else {
      localStorage.removeItem('user')
      localStorage.removeItem('token')
    }
  }, [user, token])

  const login = (role, name = '') => {
    const newUser = {
      id: Date.now().toString(),
      role,
      name: name || (role === 'student' ? 'Студент' : 'Преподаватель'),
      loginTime: new Date().toISOString()
    }
    setUser(newUser)
    setToken(null)
    return newUser
  }

  const loginWithCredentials = (authResponse) => {
    const { user: userData, access_token } = authResponse
    setUser(userData)
    setToken(access_token)
    return userData
  }

  const logout = () => {
    setUser(null)
    setToken(null)
  }

  const isStudent = () => user?.role === 'student'
  const isTeacher = () => user?.role === 'teacher'
  const isAdmin = () => user?.role === 'admin'
  const isStaff = () => user?.role === 'teacher' || user?.role === 'admin'

  const value = {
    user,
    token,
    login,
    loginWithCredentials,
    logout,
    isStudent,
    isTeacher,
    isAdmin,
    isStaff
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
