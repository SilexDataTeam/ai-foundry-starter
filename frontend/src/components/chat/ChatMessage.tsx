/* eslint-disable @typescript-eslint/no-explicit-any */

import { ToolCallExpander } from './ToolCallExpander'
import type { Message, ToolCall, ToolCallState } from '../../types/chat'

interface ChatMessageProps {
  message: Message
  toolCalls: { [key: string]: ToolCallState }
  expandedToolCall: ToolCall | null
  onToggleToolCall: (toolCall: ToolCall) => void
  isStreaming: boolean
  currentRunId: string | null
  submittedFeedback: boolean
  onFeedback: (score: number, text: string, messageId: string) => void
}

function renderRichText(
  segments: string | Array<{ type: string; text: string }>
): string {
  if (Array.isArray(segments)) {
    return segments
      .filter((part) => part.type === 'text')
      .map((part) => part.text)
      .join('\n')
  }
  return segments
}

export function ChatMessage({
  message,
  toolCalls,
  expandedToolCall,
  onToggleToolCall,
  isStreaming,
  currentRunId,
  submittedFeedback,
  onFeedback,
}: ChatMessageProps) {
  const isHuman = message.type === 'human'
  const isAi = message.type === 'ai'

  const isToolCallExpanded = (toolCall: ToolCall) => {
    return expandedToolCall === toolCall
  }

  return (
    <div className={`flex ${isHuman ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-3xl p-4 rounded-lg ${
          isHuman
            ? 'bg-primary text-white chat-bubble-human'
            : 'bg-gray-200 text-text-dark chat-bubble-ai'
        }`}
      >
        <div style={{ whiteSpace: 'pre-wrap' }}>
          {renderRichText(message.content)}
        </div>

        {isAi &&
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
                onToggle={() => onToggleToolCall(tcState.toolCall)}
              />
            )
          })}

        {isAi && !isStreaming && currentRunId && (
          <div className="mt-2 space-x-2">
            {submittedFeedback ? (
              <span>Thanks for submitting feedback</span>
            ) : (
              <>
                <button
                  onClick={() =>
                    onFeedback(1, message.content as string, message.id)
                  }
                  className="text-sm px-2 py-1 rounded bg-green-500 text-white focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-opacity-50 transition-colors"
                >
                  👍
                </button>
                <button
                  onClick={() =>
                    onFeedback(0, message.content as string, message.id)
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
}
