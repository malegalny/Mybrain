import { ConversationSummary } from './types'

type Props = {
  conversations: ConversationSummary[]
  selectedConversationId: number | null
  onSelect: (id: number) => void
}

export default function ConversationList({ conversations, selectedConversationId, onSelect }: Props) {
  return (
    <div className="panel left-pane">
      <h2>Conversations</h2>
      <ul className="conversation-list">
        {conversations.map((conversation) => (
          <li key={conversation.id}>
            <button
              className={selectedConversationId === conversation.id ? 'selected' : ''}
              onClick={() => onSelect(conversation.id)}
            >
              <strong>{conversation.title}</strong>
              <span>{conversation.source}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
