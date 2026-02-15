import { FormEvent, useMemo, useState } from 'react'
import { SearchResult } from './types'

type Props = {
  onSearch: (query: string) => Promise<SearchResult[]>
  onResultClick: (conversationId: number, messageId: number) => void
}

export default function SearchPanel({ onSearch, onResultClick }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const grouped = useMemo(() => {
    return results.reduce<Record<string, SearchResult[]>>((acc, result) => {
      const key = String(result.conversation_id)
      if (!acc[key]) acc[key] = []
      acc[key].push(result)
      return acc
    }, {})
  }, [results])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!query.trim()) {
      setResults([])
      return
    }

    setIsLoading(true)
    try {
      const data = await onSearch(query.trim())
      setResults(data)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <section className="search-panel">
      <form onSubmit={handleSubmit} className="search-form">
        <input
          type="text"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search messages"
        />
        <button type="submit">Search</button>
      </form>
      {isLoading && <p>Searching...</p>}
      {!isLoading && results.length > 0 && (
        <div className="search-results">
          {Object.entries(grouped).map(([conversationId, items]) => (
            <div key={conversationId}>
              <h4>Conversation {conversationId}</h4>
              <ul>
                {items.map((item) => (
                  <li key={item.message_id}>
                    <button onClick={() => onResultClick(item.conversation_id, item.message_id)}>
                      <small>{item.timestamp}</small>
                      <p>{item.snippet}</p>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
