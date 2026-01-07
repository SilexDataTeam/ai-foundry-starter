/* eslint-disable @typescript-eslint/no-explicit-any */

export interface StreamEvent {
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

export interface Message {
  id: string
  type: 'human' | 'ai' | 'tool'
  content: string | Array<{ type: string; text: string }>
  additional_kwargs?: Record<string, any>
  tool_calls?: ToolCall[]
  tool_call_id?: string
  name?: string
}

export interface Chat {
  title: string
  messages: Message[]
  update_time?: string
}

export interface ChatsState {
  [key: string]: Chat
}

export interface ToolCall {
  name: string
  args: Record<string, any>
  id: string
}

export interface ToolCallState {
  toolCall: ToolCall
  output: any
}

export interface ChatApiResponse {
  chats: ChatsState
}

export interface ChatTitleResponse {
  chat_title?: string
  title?: string
  error: string
}
