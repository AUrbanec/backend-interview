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
import { signUp, clearError } from '../redux/slices/authSlice'
import { AppDispatch, RootState } from '../redux/store/store'
import { useAuthContext } from '../auth/hooks'

const SignUp = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
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
    await dispatch(signUp({ email, password, fullName: fullName || undefined }))
  }

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom align="center">
            Sign Up
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => dispatch(clearError())}>
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Full Name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              margin="normal"
              autoComplete="name"
            />
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
              autoComplete="new-password"
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading}
            >
              {loading ? 'Signing up...' : 'Sign Up'}
            </Button>
          </form>

          <Typography variant="body2" align="center" sx={{ mt: 2 }}>
            Already have an account?{' '}
            <Link component={RouterLink} to="/login">
              Sign in
            </Link>
          </Typography>
        </Paper>
      </Box>
    </Container>
  )
}

export default SignUp

