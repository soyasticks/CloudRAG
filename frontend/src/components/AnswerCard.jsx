import SourceList from './SourceList'

export default function AnswerCard({ turn }) {
  return (
    <div className="chat-turn">
      <div className="chat-question">
        <strong>You:</strong> {turn.question}
      </div>

      {turn.loading && <div className="chat-loading">Thinking…</div>}

      {turn.error && <div className="error-banner">{turn.error}</div>}

      {!turn.loading && !turn.error && (
        <div className="chat-answer">
          <div className="answer-text">{turn.answer}</div>
          <SourceList sources={turn.sources} />
          <div className="latency-note">Answered in {turn.latency_ms}ms</div>
        </div>
      )}
    </div>
  )
}
