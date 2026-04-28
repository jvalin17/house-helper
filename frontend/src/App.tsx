import { BrowserRouter, Routes, Route } from "react-router-dom"
import { Toaster } from "sonner"
import Home from "@/pages/Home"
import JobDashboard from "@/pages/JobDashboard"
import ErrorBoundary from "@/components/ErrorBoundary"

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/job" element={<JobDashboard />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="bottom-right" richColors closeButton />
    </ErrorBoundary>
  )
}

export default App
