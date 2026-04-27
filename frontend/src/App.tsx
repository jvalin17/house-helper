import { BrowserRouter, Routes, Route } from "react-router-dom"
import Home from "@/pages/Home"
import JobDashboard from "@/pages/JobDashboard"
import DebugErrorBoundary from "@/components/DebugErrorBoundary"

function App() {
  return (
    <DebugErrorBoundary name="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<DebugErrorBoundary name="Home"><Home /></DebugErrorBoundary>} />
          <Route path="/job" element={<DebugErrorBoundary name="JobDashboard"><JobDashboard /></DebugErrorBoundary>} />
        </Routes>
      </BrowserRouter>
    </DebugErrorBoundary>
  )
}

export default App
