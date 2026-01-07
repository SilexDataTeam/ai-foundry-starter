/**
 * Copyright 2025 Silex Data Solutions dba Data Science Technologies, LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

import { useState, useEffect, useRef } from 'react'
import { ChevronDown, ChevronUp, Send, LogOut } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { fetchWithAuth } from '../api/client'

interface StreamEvent {
  event:
    | 'metadata'
    | 'on_tool_start'
    | 'on_tool_end'
    | 'on_retriever_start'
    | 'on_retriever_end'
    | 'on_chat_model_stream'
    | 'end'
  data?: any
  name?: string
  id?: string
  run_id?: string
}

interface Message {
  id: string
  type: 'human' | 'ai' | 'tool'
  content: string | Array<{ type: string; text: string }>
  additional_kwargs?: Record<string, any>
  tool_calls?: ToolCall[]
  tool_call_id?: string
  name?: string
}

interface Chat {
  title: string
  messages: Message[]
  update_time?: string
}

interface ChatsState {
  [key: string]: Chat
}

interface ToolCall {
  name: string
  args: Record<string, any>
  id: string
}

interface ToolCallState {
  toolCall: ToolCall
  output: any
}

const renderRichText = (
  segments: string | Array<{ type: string; text: string }>
) => {
  if (Array.isArray(segments)) {
    return segments
      .filter((part) => part.type === 'text')
      .map((part) => part.text)
      .join('\n')
  }
  return segments
}

const ToolCallExpander = ({
  toolCall,
  output,
  isExpanded,
  onToggle,
}: {
  toolCall: ToolCall
  output: any
  isExpanded: boolean
  onToggle: () => void
}) => {
  return (
    <div className="mt-2 border rounded-lg bg-gray-50">
      <button
        onClick={onToggle}
        className="w-full px-4 py-2 flex items-center justify-between text-sm text-gray-700 hover:bg-gray-100 rounded-lg"
      >
        <span>Tool Call: {toolCall.name}</span>
        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {isExpanded && (
        <div className="p-4 space-y-4 text-sm">
          <div>
            <div className="font-medium mb-2">Arguments:</div>
            <pre className="bg-gray-100 p-3 rounded overflow-auto">
              {JSON.stringify(toolCall.args, null, 2)}
            </pre>
          </div>

          <div>
            <div className="font-medium mb-2">Output:</div>
            {output && (
              <pre className="bg-gray-100 p-3 rounded overflow-auto">
                {JSON.stringify(output, null, 2)}
              </pre>
            )}
            {!output && (
              <div className="p-2 text-gray-500 italic">
                Waiting for output...
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

interface ChatApiResponse {
  chats: ChatsState
}

interface ChatTitleResponse {
  chat_title?: string
  title?: string
  error: string
}

const fetchChatTitle = async (
  messages: Message[],
  token: string | null
): Promise<string> => {
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

const ChatApp = () => {
  const { token, user, logout, isLoading: authLoading, refreshToken } = useAuth()
  const [chats, setChats] = useState<ChatsState>({})
  const [currentSessionId, setCurrentSessionId] = useState('')
  const [inputMessage, setInputMessage] = useState('')
  const [serviceUrl, setServiceUrl] = useState<string>('/')
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentRunId, setCurrentRunId] = useState<string | null>(null)
  const [toolCalls, setToolCalls] = useState<{ [key: string]: ToolCallState }>(
    {}
  )
  const [expandedToolCall, setExpandedToolCall] = useState<ToolCall | null>(
    null
  )
  const [submittedFeedback, setSubmittedFeedback] = useState<{
    [key: string]: boolean
  }>({})
  const [isLoadingChats, setIsLoadingChats] = useState(true)
  const initialLoadComplete = useRef(false)
  const [isInitialized, setIsInitialized] = useState(false)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const userScrolled = useRef(false)
  const scrollTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const toolCallRefs = useRef<{ [key: string]: ToolCall } | null>(null)

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

  useEffect(() => {
    const initializeChat = () => {
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
    }

    initializeChat()
  }, [isLoadingChats, chats, isInitialized])

  // Load chats from server when component mounts
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
                    (msg) =>
                      msg.type === 'tool' && msg.tool_call_id === toolCall.id
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
          createNewChat()
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

  // Save chats to server whenever they change
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

  const handleScroll = () => {
    if (chatContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current
      if (scrollTop + clientHeight < scrollHeight - 20) {
        userScrolled.current = true
      } else {
        userScrolled.current = false
      }
    }
  }

  const scrollToBottom = () => {
    if (chatContainerRef.current && !userScrolled.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }

  const createNewChat = () => {
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
    toolCallRefs.current = null
    userScrolled.current = false
    if (inputRef.current) {
      inputRef.current.focus()
    }
  }

  const deleteCurrentChat = async () => {
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
  }

  const appendMessage = (message: Message) => {
    setChats((prev) => ({
      ...prev,
      [currentSessionId]: {
        ...prev[currentSessionId],
        messages: [...prev[currentSessionId].messages, message],
      },
    }))
  }

  const updateLastAiMessage = (updater: (msg: Message) => Message) => {
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
  }

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isStreaming) return
    if (authLoading) return

    // Refresh token before sending
    const tokenRefreshed = await refreshToken()
    if (!tokenRefreshed) return

    userScrolled.current = false

    const userMessage: Message = {
      id: crypto.randomUUID(),
      type: 'human',
      content: inputMessage,
    }

    function expandMessagesWithTools(messages: Message[]): Message[] {
      const expanded: Message[] = []
      for (const msg of messages) {
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
    setInputMessage('')
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
    scrollTimeout.current = setTimeout(scrollToBottom, 100)

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
                  const title = await fetchChatTitle(
                    [userMessage, ...messages],
                    token
                  )
                  setChats((prev) => ({
                    ...prev,
                    [currentSessionId]: {
                      ...prev[currentSessionId],
                      title,
                    },
                  }))
                }
                if (scrollTimeout.current) {
                  clearTimeout(scrollTimeout.current)
                }
                scrollTimeout.current = setTimeout(scrollToBottom, 100)
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
  }

  const handleFeedback = async (
    score: number,
    text: string = '',
    messageId: string
  ) => {
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
  }

  const toggleToolCallExpander = (toolCall: ToolCall) => {
    setExpandedToolCall((prev) => (prev === toolCall ? null : toolCall))
  }

  const isToolCallExpanded = (toolCall: ToolCall) => {
    return expandedToolCall === toolCall
  }

  const currentChat = chats[currentSessionId]
  const messages = currentChat?.messages || []

  if (authLoading || isLoadingChats) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse text-text-light">Loading chats...</div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-secondary">
      {/* Sidebar */}
      <aside className="w-64 bg-white p-4 border-r">
        <div className="mb-6">
          <img
            src="/silex-logo.png"
            alt="Silex Logo"
            width={100}
            height={30}
          />

          <div className="mt-2 text-sm text-gray-600 border-b pb-2">
            Logged in as: {user?.email || user?.name || 'Unknown User'}
          </div>

          <div className="mt-4 space-y-2">
            <button
              onClick={createNewChat}
              className="w-full px-4 py-2 text-sm bg-primary text-white rounded hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-primary focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              disabled={isStreaming}
            >
              + New Chat
            </button>
            {!(
              Object.keys(chats).length === 1 &&
              currentChat?.messages?.length === 0
            ) && (
              <button
                onClick={deleteCurrentChat}
                className="w-full px-4 py-2 text-sm bg-red-500 text-white rounded hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                disabled={isStreaming}
              >
                Delete Chat
              </button>
            )}
            <button
              onClick={() => logout()}
              className="w-full px-4 py-2 text-sm bg-gray-500 text-white rounded hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50 flex items-center justify-center gap-2"
            >
              <LogOut size={16} />
              Logout
            </button>
          </div>
        </div>

        <div className="mb-6">
          <h3 className="font-semibold mb-2 text-text-dark">Settings</h3>
          <div className="space-y-2">
            <input
              type="text"
              value={serviceUrl}
              onChange={(e) => setServiceUrl(e.target.value)}
              className="w-full p-2 border rounded text-sm text-text-dark focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              placeholder="Service URL"
              disabled={isStreaming}
            />
          </div>
        </div>

        <div>
          <h3 className="font-semibold mb-2 text-text-dark">Recent Chats</h3>
          <div className="space-y-1">
            {Object.entries(chats).map(([id, chat]) => (
              <button
                key={id}
                onClick={() => setCurrentSessionId(id)}
                className={`w-full p-2 text-left text-sm rounded hover:bg-gray-100 text-text-dark focus:outline-none focus:bg-gray-100 transition-colors ${currentSessionId === id ? 'bg-gray-100' : ''}`}
                disabled={isStreaming}
              >
                {chat.title}
              </button>
            ))}
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        <main
          ref={chatContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto p-4 space-y-4"
        >
          {messages
            .filter((message) => message.type !== 'tool')
            .map((message, index) => {
              return (
                <div
                  key={index}
                  className={`flex ${message.type === 'human' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-3xl p-4 rounded-lg ${
                      message.type === 'human'
                        ? 'bg-primary text-white chat-bubble-human'
                        : 'bg-gray-200 text-text-dark chat-bubble-ai'
                    }`}
                  >
                    <div style={{ whiteSpace: 'pre-wrap' }}>
                      {renderRichText(message.content)}
                    </div>

                    {message.type === 'ai' &&
                      message.tool_calls &&
                      message.tool_calls.map((toolCall) => {
                        const tcState = toolCalls[toolCall.id]
                        if (!tcState) return null
                        return (
                          <ToolCallExpander
                            key={toolCall.id}
                            toolCall={tcState.toolCall}
                            output={tcState.output}
                            isExpanded={isToolCallExpanded(tcState.toolCall)}
                            onToggle={() =>
                              toggleToolCallExpander(tcState.toolCall)
                            }
                          />
                        )
                      })}

                    {message.type === 'ai' && !isStreaming && currentRunId && (
                      <div className="mt-2 space-x-2">
                        {submittedFeedback[message.id] ? (
                          <span>Thanks for submitting feedback</span>
                        ) : (
                          <>
                            <button
                              onClick={() =>
                                handleFeedback(
                                  1,
                                  message.content as string,
                                  message.id
                                )
                              }
                              className="text-sm px-2 py-1 rounded bg-green-500 text-white focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-opacity-50 transition-colors"
                            >
                              👍
                            </button>
                            <button
                              onClick={() =>
                                handleFeedback(
                                  0,
                                  message.content as string,
                                  message.id
                                )
                              }
                              className="text-sm px-2 py-1 rounded bg-red-500 text-white focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50 transition-colors"
                            >
                              👎
                            </button>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          {isStreaming && (
            <div className="flex justify-center">
              <div className="animate-pulse text-text-light">
                AI is typing...
              </div>
            </div>
          )}
        </main>

        {/* Input Area */}
        <footer className="border-t p-4 bg-white">
          <div className="flex space-x-2">
            <input
              ref={inputRef}
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              className="flex-1 p-2 border rounded text-text-dark focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              placeholder="Type your message..."
              disabled={isStreaming}
            />
            <button
              onClick={handleSendMessage}
              className={`px-4 py-2 bg-accent text-white rounded hover:bg-accent-dark focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50 transition-colors ${isStreaming ? 'opacity-50 cursor-not-allowed' : ''}`}
              disabled={isStreaming}
            >
              <Send size={16} />
            </button>
          </div>
        </footer>
      </div>
    </div>
  )
}

export default ChatApp
