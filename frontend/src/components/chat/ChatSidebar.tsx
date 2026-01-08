import { LogOut } from 'lucide-react'
import type { ChatsState } from '../../types/chat'

interface User {
  email?: string
  name?: string
  preferredUsername?: string
}

interface ChatSidebarProps {
  user: User | null
  chats: ChatsState
  currentSessionId: string
  serviceUrl: string
  isStreaming: boolean
  onNewChat: () => void
  onDeleteChat: () => void
  onSelectChat: (id: string) => void
  onServiceUrlChange: (url: string) => void
  onLogout: () => void
}

export function ChatSidebar({
  user,
  chats,
  currentSessionId,
  serviceUrl,
  isStreaming,
  onNewChat,
  onDeleteChat,
  onSelectChat,
  onServiceUrlChange,
  onLogout,
}: ChatSidebarProps) {
  const currentChat = chats[currentSessionId]
  const showDeleteButton = !(
    Object.keys(chats).length === 1 && currentChat?.messages?.length === 0
  )

  return (
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
            onClick={onNewChat}
            className="w-full px-4 py-2 text-sm bg-primary text-white rounded hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-primary focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            disabled={isStreaming}
          >
            + New Chat
          </button>
          {showDeleteButton && (
            <button
              onClick={onDeleteChat}
              className="w-full px-4 py-2 text-sm bg-red-500 text-white rounded hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              disabled={isStreaming}
            >
              Delete Chat
            </button>
          )}
          <button
            onClick={onLogout}
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
            onChange={(e) => onServiceUrlChange(e.target.value)}
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
              onClick={() => onSelectChat(id)}
              className={`w-full p-2 text-left text-sm rounded hover:bg-gray-100 text-text-dark focus:outline-none focus:bg-gray-100 transition-colors ${
                currentSessionId === id ? 'bg-gray-100' : ''
              }`}
              disabled={isStreaming}
            >
              {chat.title}
            </button>
          ))}
        </div>
      </div>
    </aside>
  )
}
