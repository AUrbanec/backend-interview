import axios from 'axios'
import { supabase } from './supabase'
import { Todo } from '../redux/slices/todosSlice'

const API_URL = import.meta.env.VITE_API_URL as string;

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
apiClient.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession()
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`
  }
  return config
})

export const authApi = {
  signUp: async (email: string, password: string, fullName?: string) => {
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
    
    // Return in the same format as the backend API for compatibility
    return {
      user: data.user,
      access_token: data.session?.access_token || '',
      refresh_token: data.session?.refresh_token || '',
    }
  },

  signIn: async (email: string, password: string) => {
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
    
    // Return in the same format as the backend API for compatibility
    return {
      user: data.user,
      access_token: data.session.access_token,
      refresh_token: data.session.refresh_token,
    }
  },

  signOut: async () => {
    const { error } = await supabase.auth.signOut()
    if (error) {
      throw error
    }
  },

  getMe: async () => {
    const { data: { user }, error } = await supabase.auth.getUser()
    if (error) {
      throw error
    }
    return { user }
  },
}

export const todosApi = {
  getTodos: async (): Promise<Todo[]> => {
    const response = await apiClient.get('/api/todos/')
    return response.data
  },

  createTodo: async (title: string, description?: string): Promise<Todo> => {
    const response = await apiClient.post('/api/todos/', {
      title,
      description,
    })
    return response.data
  },

  updateTodo: async (
    id: string,
    updates: { title?: string; description?: string; completed?: boolean }
  ): Promise<Todo> => {
    const response = await apiClient.put(`/api/todos/${id}`, updates)
    return response.data
  },

  deleteTodo: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/todos/${id}`)
  },
}

