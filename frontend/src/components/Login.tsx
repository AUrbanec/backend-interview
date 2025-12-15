import { useState, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate, Link as RouterLink } from 'react-router-dom'
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Link,
  Box,
  Alert,
} from '@mui/material'
import { signIn, clearError } from '../redux/slices/authSlice'
import { AppDispatch, RootState } from '../redux/store/store'
import { useAuthContext } from '../auth/hooks'

const Login = () => {
  const [email, setEmail] = useState('demo@ionworks.com')
  const [password, setPassword] = useState('password')
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const { loading, error } = useSelector((state: RootState) => state.auth)
  const { authenticated } = useAuthContext()

  useEffect(() => {
    if (authenticated) {
      navigate('/dashboard')
    }
  }, [authenticated, navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    dispatch(clearError())
    await dispatch(signIn({ email, password }))
  }

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom align="center">
            Sign In
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => dispatch(clearError())}>
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              margin="normal"
              required
              autoComplete="email"
            />
            <TextField
              fullWidth
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              margin="normal"
              required
              autoComplete="current-password"
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading}
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>

          <Typography variant="body2" align="center" sx={{ mt: 2 }}>
            Don't have an account?{' '}
            <Link component={RouterLink} to="/signup">
              Sign up
            </Link>
          </Typography>
        </Paper>
      </Box>
    </Container>
  )
}

export default Login

