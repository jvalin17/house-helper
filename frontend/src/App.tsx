import { BrowserRouter, Routes, Route } from "react-router-dom"
import Home from "@/pages/Home"
import JobDashboard from "@/pages/JobDashboard"

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/job" element={<JobDashboard />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
