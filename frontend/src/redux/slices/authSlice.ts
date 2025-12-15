import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import { supabase } from '../../services/supabase'

interface User {
  id: string
  email?: string
  [key: string]: any
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  loading: boolean
  error: string | null
}

const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
  loading: false,
  error: null,
}

// Async thunks
export const signUp = createAsyncThunk(
  'auth/signUp',
  async ({ email, password, fullName }: { email: string; password: string; fullName?: string }) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: fullName || '',
        },
      },
    })
    
    if (error) {
      throw error
    }
    
    if (!data.user) {
      throw new Error('Failed to create user')
    }
    
    return { user: data.user }
  }
)

export const signIn = createAsyncThunk(
  'auth/signIn',
  async ({ email, password }: { email: string; password: string }) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })
    
    if (error) {
      throw error
    }
    
    if (!data.user || !data.session) {
      throw new Error('Invalid credentials')
    }
    
    return { user: data.user }
  }
)

export const signOut = createAsyncThunk('auth/signOut', async () => {
  const { error } = await supabase.auth.signOut()
  if (error) {
    throw error
  }
})

export const checkAuth = createAsyncThunk('auth/checkAuth', async () => {
  const { data: { user } } = await supabase.auth.getUser()
  return user
})

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Sign Up
      .addCase(signUp.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(signUp.fulfilled, (state, action) => {
        state.loading = false
        state.user = action.payload.user
        state.isAuthenticated = true
      })
      .addCase(signUp.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Sign up failed'
      })
      // Sign In
      .addCase(signIn.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(signIn.fulfilled, (state, action) => {
        state.loading = false
        state.user = action.payload.user
        state.isAuthenticated = true
      })
      .addCase(signIn.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Sign in failed'
      })
      // Sign Out
      .addCase(signOut.fulfilled, (state) => {
        state.user = null
        state.isAuthenticated = false
      })
      // Check Auth
      .addCase(checkAuth.fulfilled, (state, action) => {
        if (action.payload) {
          state.user = action.payload
          state.isAuthenticated = true
        } else {
          state.user = null
          state.isAuthenticated = false
        }
      })
  },
})

export const { clearError } = authSlice.actions
export default authSlice.reducer

