import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// #region debug log
const __dbg = (location: string, message: string, data: Record<string, unknown>, hypothesisId?: string) => {
  fetch('http://127.0.0.1:7716/ingest/0b636d33-b05c-49b1-8d04-f04023f38947', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '5fd6b2' },
    body: JSON.stringify({ sessionId: '5fd6b2', location, message, data, hypothesisId, timestamp: Date.now() }),
  }).catch(() => {})
}
;(window as unknown as { __dbg: typeof __dbg }).__dbg = __dbg
window.addEventListener('error', (e) => {
  __dbg('window.onerror', 'uncaught error', {
    message: String(e.message), filename: e.filename, lineno: e.lineno, colno: e.colno,
    errorName: e.error?.name, errorMessage: e.error?.message, stack: String(e.error?.stack || '').slice(0, 2000),
  }, 'H5')
})
window.addEventListener('unhandledrejection', (e) => {
  const r = e.reason as { name?: string; message?: string; stack?: string } | string
  __dbg('window.unhandledrejection', 'unhandled promise rejection', {
    reasonName: typeof r === 'object' ? r?.name : undefined,
    reasonMessage: typeof r === 'object' ? r?.message : String(r),
    stack: typeof r === 'object' ? String(r?.stack || '').slice(0, 2000) : undefined,
  }, 'H3')
})
// #endregion

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
