import { Routes, Route, Navigate } from 'react-router-dom'
import { Container } from '@mui/material'
import Login from './components/Login'
import SignUp from './components/SignUp'
import Dashboard from './components/Dashboard'
import { useAuthContext } from './auth/hooks'

function App() {
  const { authenticated, loading } = useAuthContext()

  // Show loading state while checking auth
  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
        Loading...
      </Container>
    )
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Routes>
        <Route
          path="/login"
          element={authenticated ? <Navigate to="/dashboard" /> : <Login />}
        />
        <Route
          path="/signup"
          element={authenticated ? <Navigate to="/dashboard" /> : <SignUp />}
        />
        <Route
          path="/dashboard"
          element={authenticated ? <Dashboard /> : <Navigate to="/login" />}
        />
        <Route path="/" element={<Navigate to={authenticated ? "/dashboard" : "/login"} />} />
      </Routes>
    </Container>
  )
}

export default App

