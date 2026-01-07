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

import { useRef, useCallback, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { useChat } from '../hooks/useChat'
import { ChatSidebar, ChatMessage, ChatInput } from './chat'

export default function ChatApp() {
  const { logout } = useAuth()
  const {
    chats,
    currentSessionId,
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
    setCurrentSessionId,
    setServiceUrl,
    createNewChat,
    deleteCurrentChat,
    sendMessage,
    handleFeedback,
    toggleToolCallExpander,
  } = useChat()

  const [inputMessage, setInputMessage] = useState('')
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleScroll = useCallback(() => {
    if (chatContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current
      if (scrollTop + clientHeight < scrollHeight - 20) {
        userScrolled.current = true
      } else {
        userScrolled.current = false
      }
    }
  }, [userScrolled])

  const scrollToBottom = useCallback(() => {
    if (chatContainerRef.current && !userScrolled.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [userScrolled])

  const handleNewChat = useCallback(() => {
    createNewChat()
    inputRef.current?.focus()
  }, [createNewChat])

  const handleSendMessage = useCallback(async () => {
    if (!inputMessage.trim()) return
    await sendMessage(inputMessage)
    setInputMessage('')
    setTimeout(scrollToBottom, 100)
  }, [inputMessage, sendMessage, scrollToBottom])

  if (authLoading || isLoadingChats) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse text-text-light">Loading chats...</div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-secondary">
      <ChatSidebar
        user={user}
        chats={chats}
        currentSessionId={currentSessionId}
        serviceUrl={serviceUrl}
        isStreaming={isStreaming}
        onNewChat={handleNewChat}
        onDeleteChat={deleteCurrentChat}
        onSelectChat={setCurrentSessionId}
        onServiceUrlChange={setServiceUrl}
        onLogout={logout}
      />

      <div className="flex-1 flex flex-col">
        <main
          ref={chatContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto p-4 space-y-4"
        >
          {messages
            .filter((message) => message.type !== 'tool')
            .map((message, index) => (
              <ChatMessage
                key={index}
                message={message}
                toolCalls={toolCalls}
                expandedToolCall={expandedToolCall}
                onToggleToolCall={toggleToolCallExpander}
                isStreaming={isStreaming}
                currentRunId={currentRunId}
                submittedFeedback={submittedFeedback[message.id] || false}
                onFeedback={handleFeedback}
              />
            ))}
          {isStreaming && (
            <div className="flex justify-center">
              <div className="animate-pulse text-text-light">
                AI is typing...
              </div>
            </div>
          )}
        </main>

        <ChatInput
          ref={inputRef}
          value={inputMessage}
          onChange={setInputMessage}
          onSend={handleSendMessage}
          disabled={isStreaming}
        />
      </div>
    </div>
  )
}
