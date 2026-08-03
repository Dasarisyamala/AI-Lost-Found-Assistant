import { Navigate, Route, Routes } from 'react-router-dom'
import { Navbar } from './components/Navbar'
import { ProtectedRoute } from './components/ProtectedRoute'
import { useAuth } from './lib/auth'
import { DashboardPage } from './pages/DashboardPage'
import { LoginPage } from './pages/LoginPage'
import { MatchDetailPage } from './pages/MatchDetailPage'
import { RegisterPage } from './pages/RegisterPage'
import { ReportFoundPage } from './pages/ReportFoundPage'
import { ReportLostPage } from './pages/ReportLostPage'
import { BrowseLostPage } from './pages/BrowseLostPage'

export function App() {
  const { user } = useAuth()

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/dashboard" replace /> : <LoginPage />} />
      <Route path="/register" element={user ? <Navigate to="/dashboard" replace /> : <RegisterPage />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <div>
              <Navbar />
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/browse-lost" element={<BrowseLostPage />} />
                <Route path="/report-lost" element={<ReportLostPage />} />
                <Route path="/report-found" element={<ReportFoundPage />} />
                <Route path="/matches/:id" element={<MatchDetailPage />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </div>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}
