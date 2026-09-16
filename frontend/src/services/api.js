/**
 * Thin API client for CloudRAG backend.
 *
 * Base URL comes from Vite env var VITE_API_BASE_URL (set in frontend/.env,
 * see .env.example). Never hardcode API Gateway URLs or any credentials here.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000'

async function parseJsonOrThrow(response) {
  let data
  try {
    data = await response.json()
  } catch {
    throw new Error(`Server returned a non-JSON response (status ${response.status})`)
  }

  if (!response.ok) {
    throw new Error(data.error || `Request failed with status ${response.status}`)
  }

  return data
}

export async function uploadDocument(file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${BASE_URL}/upload?filename=${encodeURIComponent(file.name)}`)
    xhr.setRequestHeader('Content-Type', file.type || 'application/pdf')

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    }

    xhr.onload = () => {
      let data
      try {
        data = JSON.parse(xhr.responseText)
      } catch {
        reject(new Error('Server returned an invalid response'))
        return
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data)
      } else {
        reject(new Error(data.error || `Upload failed with status ${xhr.status}`))
      }
    }

    xhr.onerror = () => reject(new Error('Network error during upload'))

    xhr.send(file)
  })
}

export async function askQuestion(question) {
  const response = await fetch(`${BASE_URL}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })

  return parseJsonOrThrow(response)
}

export async function checkHealth() {
  const response = await fetch(`${BASE_URL}/health`)
  return parseJsonOrThrow(response)
}
