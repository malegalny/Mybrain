import { useEffect, useState } from 'react'
import { Attachment, ConversationDetail as ConversationDetailType } from './types'

type Props = {
  conversation: ConversationDetailType | null
  highlightedMessageId: number | null
  apiBase: string
}

const BACKEND_BASE = 'http://localhost:8000'

export default function ConversationDetail({ conversation, highlightedMessageId, apiBase }: Props) {
  const [attachments, setAttachments] = useState<Attachment[]>([])

  useEffect(() => {
    if (!highlightedMessageId) return

    const element = document.getElementById(`message-${highlightedMessageId}`)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [highlightedMessageId, conversation?.id])

  useEffect(() => {
    if (!conversation) {
      setAttachments([])
      return
    }

    fetch(`${apiBase}/conversations/${conversation.id}/attachments`)
      .then((response) => response.json())
      .then((data: Attachment[]) => setAttachments(data))
      .catch(() => setAttachments([]))
  }, [conversation?.id, apiBase])

  if (!conversation) {
    return <div className="panel">Select a conversation from the left panel.</div>
  }

  return (
    <div className="panel right-pane">
      <h2>{conversation.title}</h2>
      <div className="messages">
        {conversation.messages.map((message) => (
          <article
            id={`message-${message.id}`}
            key={message.id}
            className={`message ${message.role} ${highlightedMessageId === message.id ? 'highlighted' : ''}`}
          >
            <header>
              <strong>{message.role}</strong>
              <small>{message.timestamp}</small>
            </header>
            <p>{message.content}</p>
          </article>
        ))}
      </div>

      <section className="attachments-panel">
        <h3>Attachments</h3>
        {attachments.length === 0 && <p>No attachments for this conversation.</p>}

        {attachments.map((attachment) => {
          const src = `${BACKEND_BASE}/${attachment.local_path}`
          const mimeType = attachment.mime_type ?? ''

          if (mimeType.startsWith('image/')) {
            return (
              <div key={attachment.id} className="attachment-item">
                <p>{attachment.file_name}</p>
                <img src={src} alt={attachment.file_name} loading="lazy" />
              </div>
            )
          }

          if (mimeType.startsWith('audio/')) {
            return (
              <div key={attachment.id} className="attachment-item">
                <p>{attachment.file_name}</p>
                <audio controls src={src} />
              </div>
            )
          }

          return (
            <div key={attachment.id} className="attachment-item">
              <a href={src} target="_blank" rel="noreferrer">
                Download {attachment.file_name}
              </a>
            </div>
          )
        })}
      </section>
    </div>
  )
}
