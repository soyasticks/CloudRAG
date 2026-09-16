export default function DocumentList({ documents }) {
  if (documents.length === 0) {
    return (
      <div className="panel document-list">
        <h2>Uploaded Documents</h2>
        <p className="hint">No documents uploaded yet in this session.</p>
      </div>
    )
  }

  return (
    <div className="panel document-list">
      <h2>Uploaded Documents</h2>
      <ul>
        {documents.map((doc) => (
          <li key={doc.id}>
            <span className="doc-icon">📄</span>
            <span className="doc-name">{doc.name}</span>
            <span className={`doc-status doc-status-${doc.status}`}>{doc.status}</span>
          </li>
        ))}
      </ul>
      <p className="hint small">
        Note: newly uploaded documents are picked up on the knowledge base's next
        ingestion sync — they may not be queryable immediately.
      </p>
    </div>
  )
}
