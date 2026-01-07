/* eslint-disable @typescript-eslint/no-explicit-any */

import { useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'
import { fetchWithAuth } from '../api/client'
import type {
  Message,
  ChatsState,
  ToolCall,
  ToolCallState,
  StreamEvent,
  ChatApiResponse,
  ChatTitleResponse,
} from '../types/chat'

function sanitizeToolMessages(messages: Message[]): Message[] {
  return messages
    .filter((m) => m.type !== 'tool')
    .map((m) => {
      const { id, type, content } = m

      const sanitizedMessage: Message = {
        id,
        type,
        content,
      }

      if (m.type === 'ai') {
        sanitizedMessage.tool_calls = []
      }

      return sanitizedMessage
    })
}

async function fetchChatTitle(messages: Message[]): Promise<string> {
  try {
    const firstMessage = messages[0]?.content || ''

    const response = await fetchWithAuth('/generate_chat_title', {
      method: 'POST',
      body: JSON.stringify({
        initial_message: firstMessage,
      }),
    })

    if (!response.ok) throw new Error('Failed to fetch chat title')

    const data: ChatTitleResponse = await response.json()
    return data.chat_title || data.title || 'New Chat'
  } catch (error) {
    console.error('Error fetching chat title:', error)
    return 'New Chat'
  }
}

export function useChat() {
  const { user, isLoading: authLoading, refreshToken } = useAuth()
  const [chats, setChats] = useState<ChatsState>({})
  const [currentSessionId, setCurrentSessionId] = useState('')
  const [serviceUrl, setServiceUrl] = useState<string>('/')
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentRunId, setCurrentRunId] = useState<string | null>(null)
  const [toolCalls, setToolCalls] = useState<{ [key: string]: ToolCallState }>({})
  const [expandedToolCall, setExpandedToolCall] = useState<ToolCall | null>(null)
  const [submittedFeedback, setSubmittedFeedback] = useState<{ [key: string]: boolean }>({})
  const [isLoadingChats, setIsLoadingChats] = useState(true)
  const [isInitialized, setIsInitialized] = useState(false)

  const initialLoadComplete = useRef(false)
  const userScrolled = useRef(false)
  const scrollTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Fetch service URL on mount
  useEffect(() => {
    async function fetchServiceUrl() {
      try {
        const res = await fetchWithAuth('/config')
        if (!res.ok) {
          throw new Error('Failed to fetch service URL')
        }
        const data = await res.json()
        setServiceUrl(data.serviceUrl)
      } catch (err) {
        console.error(err)
      }
    }

    fetchServiceUrl()
  }, [])

  // Initialize empty chat if needed
  useEffect(() => {
    if (!isLoadingChats && isInitialized && Object.keys(chats).length === 0) {
      const newSessionId = crypto.randomUUID()
      setCurrentSessionId(newSessionId)
      setChats({
        [newSessionId]: {
          title: 'Empty chat',
          messages: [],
        },
      })
    }
  }, [isLoadingChats, chats, isInitialized])

  // Load chats from server
  useEffect(() => {
    if (authLoading) return
    if (!user) return
    if (initialLoadComplete.current) return

    const fetchChats = async () => {
      setIsLoadingChats(true)
      try {
        console.log('Fetching initial chats...')
        const response = await fetchWithAuth('/chats')

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          console.error('Failed to fetch chats:', {
            status: response.status,
            statusText: response.statusText,
            error: errorData.error,
          })
          return
        }

        const data = (await response.json()) as ChatApiResponse
        if (data.chats && Object.keys(data.chats).length > 0) {
          console.log('Loaded chats:', Object.keys(data.chats).length)
          setChats(data.chats)
          setCurrentSessionId(Object.keys(data.chats)[0])

          // Initialize tool calls from saved messages
          const toolCallsMap: { [key: string]: ToolCallState } = {}
          Object.values(data.chats).forEach((chat) => {
            chat.messages.forEach((message) => {
              if (message.type === 'ai' && message.tool_calls) {
                message.tool_calls.forEach((toolCall) => {
                  const toolResponse = chat.messages.find(
                    (msg) => msg.type === 'tool' && msg.tool_call_id === toolCall.id
                  )

                  let parsedOutput = null
                  if (toolResponse) {
                    try {
                      parsedOutput =
                        typeof toolResponse.content === 'string'
                          ? JSON.parse(toolResponse.content)
                          : toolResponse.content
                    } catch (e) {
                      console.error('Error parsing tool response:', e)
                      parsedOutput = toolResponse.content
                    }
                  }

                  toolCallsMap[toolCall.id] = {
                    toolCall,
                    output: parsedOutput,
                  }
                })
              }
            })
          })
          setToolCalls(toolCallsMap)
        } else {
          console.log('No existing chats, creating new chat')
          const newSessionId = crypto.randomUUID()
          setCurrentSessionId(newSessionId)
          setChats({
            [newSessionId]: {
              title: 'Empty chat',
              messages: [],
            },
          })
        }
        initialLoadComplete.current = true
        setIsInitialized(true)
      } catch (error) {
        console.error('Error fetching chats:', error)
      } finally {
        setIsLoadingChats(false)
      }
    }

    fetchChats()
  }, [user, authLoading])

  // Save chats to server
  useEffect(() => {
    if (!user) return
    if (isLoadingChats) return
    if (!isInitialized) return
    if (!initialLoadComplete.current) return
    if (Object.keys(chats).length === 0) return

    const saveChats = async () => {
      try {
        console.log('Saving chats:', Object.keys(chats).length)
        const response = await fetchWithAuth('/chats', {
          method: 'POST',
          body: JSON.stringify({ chats }),
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          console.error('Failed to save chats:', {
            status: response.status,
            statusText: response.statusText,
            error: errorData.error,
          })
        }
      } catch (error) {
        console.error('Error saving chats:', error)
      }
    }

    const timeoutId = setTimeout(saveChats, 1000)
    return () => clearTimeout(timeoutId)
  }, [chats, user, isLoadingChats, isInitialized])

  const currentChat = chats[currentSessionId]
  const messages = currentChat?.messages || []

  const appendMessage = useCallback(
    (message: Message) => {
      setChats((prev) => ({
        ...prev,
        [currentSessionId]: {
          ...prev[currentSessionId],
          messages: [...prev[currentSessionId].messages, message],
        },
      }))
    },
    [currentSessionId]
  )

  const updateLastAiMessage = useCallback(
    (updater: (msg: Message) => Message) => {
      setChats((prev) => {
        const chat = prev[currentSessionId]
        const updatedMessages = [...chat.messages]
        let lastAiIndex = -1
        for (let i = updatedMessages.length - 1; i >= 0; i--) {
          if (updatedMessages[i].type === 'ai') {
            lastAiIndex = i
            break
          }
        }

        if (lastAiIndex === -1) {
          const newAiMessage = updater({
            id: crypto.randomUUID(),
            type: 'ai',
            content: '',
            tool_calls: [],
          })
          updatedMessages.push(newAiMessage)
        } else {
          updatedMessages[lastAiIndex] = updater(updatedMessages[lastAiIndex])
        }

        return {
          ...prev,
          [currentSessionId]: {
            ...chat,
            messages: updatedMessages,
          },
        }
      })
    },
    [currentSessionId]
  )

  const createNewChat = useCallback(() => {
    const newSessionId = crypto.randomUUID()
    setCurrentSessionId(newSessionId)
    setChats((prev) => ({
      ...prev,
      [newSessionId]: {
        title: 'Empty chat',
        messages: [],
      },
    }))
    setToolCalls({})
    setCurrentRunId(null)
    setExpandedToolCall(null)
    userScrolled.current = false
  }, [])

  const deleteCurrentChat = useCallback(async () => {
    if (!currentSessionId) return

    try {
      const response = await fetchWithAuth(`/chats/${currentSessionId}`, {
        method: 'DELETE',
      })

      if (response.status === 404) {
        console.warn('Chat already deleted or not found, ignoring...')
      } else if (!response.ok) {
        console.error('Failed to delete chat:', response.statusText)
        return
      }
    } catch (error) {
      console.error('Error calling DELETE /chats:', error)
      return
    }

    setChats((prevChats) => {
      const newChats = { ...prevChats }
      delete newChats[currentSessionId]

      const remainingIds = Object.keys(newChats)
      if (remainingIds.length === 0) {
        const newId = crypto.randomUUID()
        newChats[newId] = { title: 'Empty chat', messages: [] }
        setCurrentSessionId(newId)
      } else {
        setCurrentSessionId(remainingIds[0])
      }

      return newChats
    })
  }, [currentSessionId])

  const sendMessage = useCallback(
    async (inputMessage: string) => {
      if (!inputMessage.trim() || isStreaming) return
      if (authLoading) return

      const tokenRefreshed = await refreshToken()
      if (!tokenRefreshed) return

      userScrolled.current = false

      const userMessage: Message = {
        id: crypto.randomUUID(),
        type: 'human',
        content: inputMessage,
      }

      function expandMessagesWithTools(msgs: Message[]): Message[] {
        const expanded: Message[] = []
        for (const msg of msgs) {
          expanded.push(msg)

          if (msg.type === 'ai' && msg.tool_calls) {
            for (const toolCall of msg.tool_calls) {
              const toolResponse = toolCalls[toolCall.id]
              if (toolResponse?.output) {
                expanded.push({
                  id: crypto.randomUUID(),
                  type: 'tool',
                  content: JSON.stringify(toolResponse.output),
                  tool_call_id: toolCall.id,
                  name: toolCall.name,
                  additional_kwargs: {},
                })
              }
            }
          }
        }
        return expanded
      }

      const fullConversation = chats[currentSessionId].messages
      const expandedConversation = expandMessagesWithTools(fullConversation)
      const allMessages = [...expandedConversation, userMessage]
      const sanitizedMessages = sanitizeToolMessages(allMessages)

      console.log('Messages being sent:', JSON.stringify(sanitizedMessages, null, 2))

      const isFirstMessage = messages.length === 0
      appendMessage(userMessage)
      setIsStreaming(true)

      appendMessage({
        id: crypto.randomUUID(),
        type: 'ai',
        content: '',
        tool_calls: [],
      })

      if (scrollTimeout.current) {
        clearTimeout(scrollTimeout.current)
      }

      try {
        const response = await fetchWithAuth(`${serviceUrl}stream_events`, {
          method: 'POST',
          headers: {
            Accept: 'text/event-stream',
          },
          body: JSON.stringify({
            input_data: {
              messages: sanitizedMessages,
              user_id: user?.email || 'unknown',
              session_id: currentSessionId,
            },
          }),
        })

        if (response.status === 401) {
          return
        }

        const reader = response.body?.getReader()
        if (!reader) throw new Error('No reader available')

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.trim()) continue

            try {
              const event: StreamEvent = JSON.parse(line)

              switch (event.event) {
                case 'metadata':
                  setCurrentRunId(event.data?.run_id || null)
                  break

                case 'on_chat_model_stream':
                  if (event.data?.chunk?.content) {
                    const chunkText = event.data.chunk.content
                    updateLastAiMessage((msg) => ({
                      ...msg,
                      content:
                        typeof msg.content === 'string'
                          ? msg.content + chunkText
                          : msg.content + chunkText,
                    }))
                  }
                  break

                case 'on_tool_start':
                  if (event.name && event.data?.input && event.run_id) {
                    const toolCall: ToolCall = {
                      name: event.name,
                      args: event.data.input,
                      id: event.run_id,
                    }

                    setToolCalls((prev) => ({
                      ...prev,
                      [toolCall.id]: {
                        toolCall,
                        output: null,
                      },
                    }))

                    updateLastAiMessage((msg) => {
                      const tcs = msg.tool_calls || []
                      return {
                        ...msg,
                        tool_calls: [...tcs, toolCall],
                      }
                    })
                  }
                  break

                case 'on_tool_end':
                  if (event.run_id && event.data?.output) {
                    const toolCallId = event.run_id
                    setToolCalls((prev) => {
                      const existing = prev[toolCallId]
                      if (!existing) return prev

                      return {
                        ...prev,
                        [toolCallId]: {
                          ...existing,
                          output: event.data.output,
                        },
                      }
                    })

                    const toolMessage: Message = {
                      id: crypto.randomUUID(),
                      type: 'tool',
                      content: JSON.stringify(event.data.output),
                      tool_call_id: toolCallId,
                      name: event.name,
                      additional_kwargs: {},
                    }
                    appendMessage(toolMessage)
                  }
                  break

                case 'end':
                  setIsStreaming(false)
                  if (isFirstMessage) {
                    const title = await fetchChatTitle([userMessage, ...messages])
                    setChats((prev) => ({
                      ...prev,
                      [currentSessionId]: {
                        ...prev[currentSessionId],
                        title,
                      },
                    }))
                  }
                  break
              }
            } catch (e) {
              console.error('Error parsing event:', e)
            }
          }
        }
      } catch (error) {
        console.error('Error during streaming:', error)
        setIsStreaming(false)
      }
    },
    [
      isStreaming,
      authLoading,
      refreshToken,
      toolCalls,
      chats,
      currentSessionId,
      messages,
      appendMessage,
      updateLastAiMessage,
      serviceUrl,
      user,
    ]
  )

  const handleFeedback = useCallback(
    async (score: number, text: string = '', messageId: string) => {
      if (!currentRunId) return

      try {
        await fetchWithAuth(`${serviceUrl}feedback`, {
          method: 'POST',
          body: JSON.stringify({
            score,
            text,
            run_id: currentRunId,
            log_type: 'feedback',
          }),
        })
        setSubmittedFeedback((prev) => ({ ...prev, [messageId]: true }))
      } catch (error) {
        console.error('Error sending feedback:', error)
      }
    },
    [currentRunId, serviceUrl]
  )

  const toggleToolCallExpander = useCallback((toolCall: ToolCall) => {
    setExpandedToolCall((prev) => (prev === toolCall ? null : toolCall))
  }, [])

  return {
    // State
    chats,
    currentSessionId,
    currentChat,
    messages,
    serviceUrl,
    isStreaming,
    currentRunId,
    toolCalls,
    expandedToolCall,
    submittedFeedback,
    isLoadingChats,
    authLoading,
    user,
    userScrolled,

    // Actions
    setCurrentSessionId,
    setServiceUrl,
    createNewChat,
    deleteCurrentChat,
    sendMessage,
    handleFeedback,
    toggleToolCallExpander,
  }
}
