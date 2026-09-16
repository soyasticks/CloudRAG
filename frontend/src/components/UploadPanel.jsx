import { useState, useRef } from 'react'
import { uploadDocument } from '../services/api'

export default function UploadPanel({ onUploaded }) {
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const handleFileChange = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    setError(null)

    if (file.type !== 'application/pdf') {
      setError('Only PDF files are supported.')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('File exceeds the 10MB limit.')
      return
    }

    setProgress(0)
    try {
      const result = await uploadDocument(file, setProgress)
      onUploaded({
        id: result.documentId,
        name: file.name,
        status: result.status,
      })
    } catch (err) {
      setError(err.message || 'Upload failed. Please try again.')
    } finally {
      setProgress(null)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div className="panel upload-panel">
      <h2>Upload Policy Document</h2>
      <p className="hint">PDF only, up to 10MB.</p>

      <label className="file-drop">
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          onChange={handleFileChange}
          disabled={progress !== null}
        />
        {progress === null ? 'Choose a PDF or drag it here' : `Uploading… ${progress}%`}
      </label>

      {progress !== null && (
        <div className="progress-bar">
          <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
        </div>
      )}

      {error && <div className="error-banner">{error}</div>}
    </div>
  )
}
