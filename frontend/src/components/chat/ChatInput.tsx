import { forwardRef } from 'react'
import { Send } from 'lucide-react'

interface ChatInputProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  disabled: boolean
}

export const ChatInput = forwardRef<HTMLInputElement, ChatInputProps>(
  function ChatInput({ value, onChange, onSend, disabled }, ref) {
    const handleKeyPress = (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        onSend()
      }
    }

    return (
      <footer className="border-t p-4 bg-white">
        <div className="flex space-x-2">
          <input
            ref={ref}
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyPress={handleKeyPress}
            className="flex-1 p-2 border rounded text-text-dark focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            placeholder="Type your message..."
            disabled={disabled}
          />
          <button
            onClick={onSend}
            className={`px-4 py-2 bg-accent text-white rounded hover:bg-accent-dark focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50 transition-colors ${
              disabled ? 'opacity-50 cursor-not-allowed' : ''
            }`}
            disabled={disabled}
          >
            <Send size={16} />
          </button>
        </div>
      </footer>
    )
  }
)
