import { useEffect } from 'react'
import { ConversationDetail as ConversationDetailType } from './types'

type Props = {
  conversation: ConversationDetailType | null
  highlightedMessageId: number | null
}

export default function ConversationDetail({ conversation, highlightedMessageId }: Props) {
  useEffect(() => {
    if (!highlightedMessageId) return

    const element = document.getElementById(`message-${highlightedMessageId}`)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [highlightedMessageId, conversation?.id])

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
    </div>
  )
}
