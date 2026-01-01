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

  useEffect(() => {
    if (user) {
      localStorage.setItem('user', JSON.stringify(user))
    } else {
      localStorage.removeItem('user')
    }
  }, [user])

  const login = (role, name = '') => {
    const newUser = {
      id: Date.now().toString(),
      role, // 'student' или 'teacher'
      name: name || (role === 'student' ? 'Студент' : 'Преподаватель'),
      loginTime: new Date().toISOString()
    }
    setUser(newUser)
    return newUser
  }

  const logout = () => {
    setUser(null)
  }

  const isStudent = () => user?.role === 'student'
  const isTeacher = () => user?.role === 'teacher'

  const value = {
    user,
    login,
    logout,
    isStudent,
    isTeacher
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

