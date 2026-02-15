export type ConversationSummary = {
  id: number
  title: string
  source: string
  created_at: string
}

export type Message = {
  id: number
  conversation_id: number
  role: string
  content: string
  timestamp: string
}

export type ConversationDetail = {
  id: number
  title: string
  source: string
  created_at: string
  updated_at: string
  messages: Message[]
}

export type SearchResult = {
  conversation_id: number
  message_id: number
  snippet: string
  timestamp: string
}

export type Attachment = {
  id: number
  conversation_id: number
  message_id: number | null
  file_id: string | null
  file_name: string
  mime_type: string | null
  local_path: string
  created_at: string
}
