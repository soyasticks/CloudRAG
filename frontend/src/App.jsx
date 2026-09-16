import { useState } from 'react'
import UploadPanel from './components/UploadPanel'
import DocumentList from './components/DocumentList'
import ChatInterface from './components/ChatInterface'

export default function App() {
  const [documents, setDocuments] = useState([])

  const handleUploaded = (doc) => {
    setDocuments((prev) => [...prev, doc])
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>CloudRAG</h1>
        <p>Enterprise Policy Document Q&A</p>
      </header>

      <main className="app-grid">
        <div className="app-sidebar">
          <UploadPanel onUploaded={handleUploaded} />
          <DocumentList documents={documents} />
        </div>

        <div className="app-main">
          <ChatInterface />
        </div>
      </main>
    </div>
  )
}
