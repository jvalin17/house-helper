import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// #region agent log
const __dbgLog = (location: string, message: string, data: Record<string, unknown> = {}) => {
  fetch('http://127.0.0.1:7716/ingest/0b636d33-b05c-49b1-8d04-f04023f38947', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '5fd6b2' },
    body: JSON.stringify({ sessionId: '5fd6b2', location, message, data, timestamp: Date.now() }),
  }).catch(() => {})
}
;(window as unknown as { __dbgLog: typeof __dbgLog }).__dbgLog = __dbgLog
window.addEventListener('error', (e) => {
  __dbgLog('main.tsx:window.onerror', 'window error', {
    hypothesisId: 'GLOBAL',
    message: String(e.message),
    filename: String(e.filename),
    lineno: e.lineno, colno: e.colno,
    stack: e.error && (e.error as Error).stack ? String((e.error as Error).stack).slice(0, 2000) : null,
  })
})
window.addEventListener('unhandledrejection', (e) => {
  const reason = e.reason as { message?: string; stack?: string } | string | undefined
  __dbgLog('main.tsx:unhandledrejection', 'unhandled promise rejection', {
    hypothesisId: 'GLOBAL',
    reason: typeof reason === 'string' ? reason : reason?.message || JSON.stringify(reason),
    stack: typeof reason === 'object' && reason?.stack ? String(reason.stack).slice(0, 2000) : null,
  })
})
__dbgLog('main.tsx:boot', 'app boot', { url: window.location.href })
// #endregion

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
