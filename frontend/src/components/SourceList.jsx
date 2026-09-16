export default function SourceList({ sources }) {
  if (!sources || sources.length === 0) {
    return <p className="hint small">No source documents were returned for this answer.</p>
  }

  return (
    <div className="source-list">
      <h4>Sources</h4>
      <ul>
        {sources.map((source, idx) => (
          <li key={idx}>
            📄 {source.document} — Page {source.page}
            {source.excerpt && <div className="excerpt">"{source.excerpt}"</div>}
          </li>
        ))}
      </ul>
    </div>
  )
}
