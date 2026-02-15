import { useEffect, useState } from 'react'
import ConversationDetail from './components/ConversationDetail'
import ConversationList from './components/ConversationList'
import SearchPanel from './components/SearchPanel'
import { ConversationDetail as ConversationDetailType, ConversationSummary, SearchResult } from './components/types'

const API_BASE = 'http://localhost:8000/api'

export default function App() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null)
  const [selectedConversation, setSelectedConversation] = useState<ConversationDetailType | null>(null)
  const [highlightedMessageId, setHighlightedMessageId] = useState<number | null>(null)

  useEffect(() => {
    loadConversations().catch(console.error)
  }, [])

  useEffect(() => {
    if (selectedConversationId === null) return
    loadConversation(selectedConversationId).catch(console.error)
  }, [selectedConversationId])

  async function loadConversations() {
    const response = await fetch(`${API_BASE}/conversations`)
    const data: ConversationSummary[] = await response.json()
    setConversations(data)
    if (data.length > 0 && selectedConversationId === null) {
      setSelectedConversationId(data[0].id)
    }
  }

  async function loadConversation(id: number) {
    const response = await fetch(`${API_BASE}/conversations/${id}`)
    const data: ConversationDetailType = await response.json()
    setSelectedConversation(data)
  }

  async function handleSearch(query: string): Promise<SearchResult[]> {
    const response = await fetch(`${API_BASE}/search?query=${encodeURIComponent(query)}`)
    return response.json()
  }

  async function handleResultClick(conversationId: number, messageId: number) {
    setSelectedConversationId(conversationId)
    setHighlightedMessageId(messageId)
  }

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    if (!event.target.files?.length) return

    const formData = new FormData()
    Array.from(event.target.files).forEach((file) => formData.append('files', file))

    await fetch(`${API_BASE}/upload`, {
      method: 'POST',
      body: formData,
    })

    await loadConversations()
  }

  return (
    <div className="app-container">
      <aside>
        <div className="panel upload-panel">
          <h1>AI Chat Archive</h1>
          <input type="file" accept="application/json,.zip,application/zip" multiple onChange={handleUpload} />
        </div>
        <ConversationList
          conversations={conversations}
          selectedConversationId={selectedConversationId}
          onSelect={(id) => {
            setSelectedConversationId(id)
            setHighlightedMessageId(null)
          }}
        />
      </aside>
      <main>
        <SearchPanel onSearch={handleSearch} onResultClick={handleResultClick} />
        <ConversationDetail conversation={selectedConversation} highlightedMessageId={highlightedMessageId} apiBase={API_BASE} />
      </main>
    </div>
  )
}
