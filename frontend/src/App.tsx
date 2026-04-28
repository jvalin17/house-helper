import { BrowserRouter, Routes, Route } from "react-router-dom"
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
    </ErrorBoundary>
  )
}

export default App
