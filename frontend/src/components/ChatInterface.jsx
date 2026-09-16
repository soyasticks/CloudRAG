import { useState } from 'react'
import { askQuestion } from '../services/api'
import AnswerCard from './AnswerCard'

export default function ChatInterface() {
  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState([])
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (event) => {
    event.preventDefault()
    const trimmed = question.trim()
    if (!trimmed || submitting) return

    const turnIndex = turns.length
    setTurns((prev) => [...prev, { question: trimmed, loading: true }])
    setQuestion('')
    setSubmitting(true)

    try {
      const data = await askQuestion(trimmed)
      setTurns((prev) => {
        const next = [...prev]
        next[turnIndex] = {
          question: trimmed,
          loading: false,
          answer: data.answer,
          sources: data.sources,
          ...data, // includes latencyMs, requestId from the backend as-is
        }
        return next
      })
    } catch (err) {
      setTurns((prev) => {
        const next = [...prev]
        next[turnIndex] = {
          question: trimmed,
          loading: false,
          error: err.message || 'Something went wrong. Please try again.',
        }
        return next
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="panel chat-panel">
      <h2>Ask a Question</h2>

      <div className="chat-history">
        {turns.length === 0 && (
          <p className="hint">
            Ask something like "How many annual leave days are employees entitled to?"
          </p>
        )}
        {turns.map((turn, idx) => (
          <AnswerCard key={idx} turn={turn} />
        ))}
      </div>

      <form className="chat-input-row" onSubmit={handleSubmit}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about the uploaded policies…"
          disabled={submitting}
        />
        <button type="submit" disabled={submitting || !question.trim()}>
          {submitting ? 'Asking…' : 'Ask'}
        </button>
      </form>
    </div>
  )
}
