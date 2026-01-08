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

  createTodo: async (title: string, description?: string, simulation_id?: string): Promise<Todo> => {
    const response = await apiClient.post('/api/todos/', {
      title,
      description,
      simulation_id,
    })
    return response.data
  },

  updateTodo: async (
    id: string,
    updates: { title?: string; description?: string; completed?: boolean; simulation_id?: string | null }
  ): Promise<Todo> => {
    const response = await apiClient.put(`/api/todos/${id}`, updates)
    return response.data
  },

  deleteTodo: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/todos/${id}`)
  },
}

// Simulations API
export interface CreateSimulationParams {
  name: string
  description?: string
  chemistry?: string
  c_rate?: number
  temperature_celsius?: number
  cycles?: number
  custom_parameters?: Record<string, unknown>
}

export const simulationsApi = {
  getSimulations: async () => {
    const response = await apiClient.get('/api/simulations/')
    return response.data
  },

  getSimulation: async (id: string) => {
    const response = await apiClient.get(`/api/simulations/${id}`)
    return response.data
  },

  createSimulation: async (params: CreateSimulationParams) => {
    const response = await apiClient.post('/api/simulations/', params)
    return response.data
  },

  deleteSimulation: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/simulations/${id}`)
  },

  cancelSimulation: async (id: string): Promise<void> => {
    await apiClient.post(`/api/simulations/${id}/cancel`)
  },
}

// Presets API
export interface CreatePresetParams {
  name: string
  description?: string
  is_public?: boolean
  chemistry?: string
  c_rate?: number
  temperature_celsius?: number
  cycles?: number
  custom_parameters?: Record<string, unknown>
}

export interface UpdatePresetParams {
  name?: string
  description?: string
  is_public?: boolean
  chemistry?: string
  c_rate?: number
  temperature_celsius?: number
  cycles?: number
  custom_parameters?: Record<string, unknown>
}

export const presetsApi = {
  getPresets: async () => {
    const response = await apiClient.get('/api/presets/')
    return response.data
  },

  getPreset: async (id: string) => {
    const response = await apiClient.get(`/api/presets/${id}`)
    return response.data
  },

  createPreset: async (params: CreatePresetParams) => {
    const response = await apiClient.post('/api/presets/', params)
    return response.data
  },

  updatePreset: async (id: string, params: UpdatePresetParams) => {
    const response = await apiClient.put(`/api/presets/${id}`, params)
    return response.data
  },

  deletePreset: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/presets/${id}`)
  },

  duplicatePreset: async (id: string, newName?: string) => {
    const response = await apiClient.post(`/api/presets/${id}/duplicate`, { new_name: newName })
    return response.data
  },
}

// Usage API
export const usageApi = {
  getUsage: async () => {
    const response = await apiClient.get('/api/usage/')
    return response.data
  },

  getUsageSummary: async () => {
    const response = await apiClient.get('/api/usage/summary')
    return response.data
  },

  getApiLogs: async (limit = 100, offset = 0) => {
    const response = await apiClient.get(`/api/usage/logs?limit=${limit}&offset=${offset}`)
    return response.data
  },
}

