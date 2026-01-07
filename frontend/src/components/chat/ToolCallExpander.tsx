/* eslint-disable @typescript-eslint/no-explicit-any */

import { ChevronDown, ChevronUp } from 'lucide-react'
import type { ToolCall } from '../../types/chat'

interface ToolCallExpanderProps {
  toolCall: ToolCall
  output: any
  isExpanded: boolean
  onToggle: () => void
}

export function ToolCallExpander({
  toolCall,
  output,
  isExpanded,
  onToggle,
}: ToolCallExpanderProps) {
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
