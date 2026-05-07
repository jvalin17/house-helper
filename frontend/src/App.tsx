import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { Toaster } from "sonner"
import Home from "@/pages/Home"
import JobDashboard from "@/pages/JobDashboard"
import ApartmentDashboard from "@/pages/ApartmentDashboard"
import GlobalSettings from "@/pages/GlobalSettings"
import Login from "@/pages/Login"
import Signup from "@/pages/Signup"
import ErrorBoundary from "@/components/ErrorBoundary"
import { useAuth } from "@/hooks/useAuth"

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, authMode } = useAuth()

  if (isLoading) {
    return <div className="min-h-screen flex items-center justify-center text-muted-foreground">Loading...</div>
  }

  // Local mode — always authenticated
  if (authMode === "local") return <>{children}</>

  // Multi mode — require login
  if (!isAuthenticated) return <Navigate to="/login" />

  return <>{children}</>
}

function App() {
  const { login, signup, authMode, isLoading } = useAuth()

  if (isLoading) {
    return <div className="min-h-screen flex items-center justify-center text-muted-foreground">Loading...</div>
  }

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          {authMode === "multi" && (
            <>
              <Route path="/login" element={<Login onLogin={login} />} />
              <Route path="/signup" element={<Signup onSignup={signup} />} />
            </>
          )}
          <Route path="/" element={<AuthGuard><Home /></AuthGuard>} />
          <Route path="/job" element={<AuthGuard><JobDashboard /></AuthGuard>} />
          <Route path="/apartments" element={<AuthGuard><ApartmentDashboard /></AuthGuard>} />
          <Route path="/settings" element={<AuthGuard><GlobalSettings /></AuthGuard>} />
        </Routes>
      </BrowserRouter>
      <Toaster position="bottom-right" richColors closeButton />
    </ErrorBoundary>
  )
}

export default App
