import React, { createContext, useContext, useState, useEffect } from 'react'

const ChatContext = createContext()

export const useChat = () => {
  const context = useContext(ChatContext)
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider')
  }
  return context
}

export const ChatProvider = ({ children }) => {
  const [chats, setChats] = useState(() => {
    const saved = localStorage.getItem('chats')
    return saved ? JSON.parse(saved) : []
  })

  const [knowledgeBase, setKnowledgeBase] = useState(() => {
    const saved = localStorage.getItem('knowledgeBase')
    return saved ? JSON.parse(saved) : []
  })

  const [currentChatId, setCurrentChatId] = useState(null)

  useEffect(() => {
    localStorage.setItem('chats', JSON.stringify(chats))
  }, [chats])

  useEffect(() => {
    localStorage.setItem('knowledgeBase', JSON.stringify(knowledgeBase))
  }, [knowledgeBase])

  const createChat = (title = 'Новый экзамен') => {
    const newChat = {
      id: Date.now().toString(),
      title,
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }
    setChats(prev => [newChat, ...prev])
    return newChat.id
  }

  const deleteChat = (chatId) => {
    setChats(prev => prev.filter(chat => chat.id !== chatId))
    if (currentChatId === chatId) {
      setCurrentChatId(null)
    }
  }

  const updateChatTitle = (chatId, title) => {
    setChats(prev =>
      prev.map(chat =>
        chat.id === chatId
          ? { ...chat, title, updatedAt: new Date().toISOString() }
          : chat
      )
    )
  }

  const addMessage = (chatId, message) => {
    setChats(prev =>
      prev.map(chat => {
        if (chat.id === chatId) {
          return {
            ...chat,
            messages: [...chat.messages, message],
            updatedAt: new Date().toISOString()
          }
        }
        return chat
      })
    )
  }

  const getChat = (chatId) => {
    return chats.find(chat => chat.id === chatId)
  }

  // База знаний (только для преподавателей)
  const addKnowledgeItem = (item) => {
    const newItem = {
      id: Date.now().toString(),
      ...item,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }
    setKnowledgeBase(prev => [newItem, ...prev])
    return newItem.id
  }

  const updateKnowledgeItem = (id, updates) => {
    setKnowledgeBase(prev =>
      prev.map(item =>
        item.id === id
          ? { ...item, ...updates, updatedAt: new Date().toISOString() }
          : item
      )
    )
  }

  const deleteKnowledgeItem = (id) => {
    setKnowledgeBase(prev => prev.filter(item => item.id !== id))
  }

  const getKnowledgeItem = (id) => {
    return knowledgeBase.find(item => item.id === id)
  }

  const searchKnowledgeBase = (query) => {
    const lowerQuery = query.toLowerCase()
    return knowledgeBase.filter(item =>
      item.title?.toLowerCase().includes(lowerQuery) ||
      item.content?.toLowerCase().includes(lowerQuery) ||
      item.tags?.some(tag => tag.toLowerCase().includes(lowerQuery))
    )
  }

  const value = {
    chats,
    knowledgeBase,
    currentChatId,
    setCurrentChatId,
    createChat,
    deleteChat,
    updateChatTitle,
    addMessage,
    getChat,
    addKnowledgeItem,
    updateKnowledgeItem,
    deleteKnowledgeItem,
    getKnowledgeItem,
    searchKnowledgeBase
  }

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

