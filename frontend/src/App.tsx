import { Routes, Route, Navigate } from 'react-router-dom'
import { Container, Box } from '@mui/material'
import Login from './components/Login'
import SignUp from './components/SignUp'
import Dashboard from './components/Dashboard'
import SimulationDashboard from './components/SimulationDashboard'
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
    <Box>
      <Routes>
        <Route
          path="/login"
          element={authenticated ? <Navigate to="/simulations" /> : <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}><Login /></Container>}
        />
        <Route
          path="/signup"
          element={authenticated ? <Navigate to="/simulations" /> : <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}><SignUp /></Container>}
        />
        <Route
          path="/dashboard"
          element={authenticated ? <Dashboard /> : <Navigate to="/login" />}
        />
        <Route
          path="/simulations"
          element={authenticated ? <SimulationDashboard /> : <Navigate to="/login" />}
        />
        <Route path="/" element={<Navigate to={authenticated ? "/simulations" : "/login"} />} />
      </Routes>
    </Box>
  )
}

export default App

