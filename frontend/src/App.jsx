import React, { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || ''

export default function App() {
  const [status, setStatus] = useState('Loading backend status...')

  useEffect(() => {
    // Try a simple backend health endpoint; user can adjust path if needed.
    const url = API_BASE ? `${API_BASE}/docs` : '/api/docs'
    fetch(url, { mode: 'cors' })
      .then(res => {
        setStatus(res.ok ? `Backend reachable: ${res.status}` : `Backend error: ${res.status}`)
      })
      .catch(err => setStatus(`Backend request failed: ${err.message}`))
  }, [])

  return (
    <div style={{fontFamily:'system-ui, -apple-system, Arial', padding: 24}}>
      <h1 style={{marginTop:0}}>Pet Med AI — Frontend</h1>
      <p>Vite + React scaffold is working.</p>
      <p><strong>Backend status:</strong> {status}</p>
      <p style={{opacity:.8, fontSize:14}}>
        Tip: set <code>VITE_API_BASE</code> env var on Render Static Site to your backend base URL (e.g. <code>https://pet-med-ai-backend.onrender.com</code>).
      </p>
    </div>
  )
}
