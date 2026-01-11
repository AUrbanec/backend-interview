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

// Experiment types
export interface ExperimentStep {
  step_type: 'current' | 'c_rate' | 'voltage' | 'power' | 'resistance' | 'rest' | 'string'
  value?: number
  value_unit?: string
  duration?: string
  termination?: string
  period?: string
  temperature?: string
  tags?: string[]
  direction?: 'charge' | 'discharge'
  step_string?: string
  drive_cycle_data?: number[][]
  drive_cycle_type?: 'current' | 'power' | 'voltage'
}

export interface ExperimentCycle {
  steps: ExperimentStep[]
  repeat: number
}

export interface ExperimentDefinition {
  cycles: ExperimentCycle[]
  default_period?: string
  default_temperature_celsius?: number
}

export type ExperimentMode = 'protocol' | 'custom' | 'template'

// Simulations API
export interface CreateSimulationParams {
  name: string
  description?: string
  // Cell & Model
  parameter_set?: string
  chemistry?: string
  model_type?: string
  model_options?: Record<string, string>
  // Experiment
  protocol?: string
  c_rate?: number
  temperature_celsius?: number
  cycles?: number
  experiment_mode?: ExperimentMode
  experiment_definition?: ExperimentDefinition
  experiment_template_id?: string
  experiment_period?: string
  // Additional
  custom_parameters?: Record<string, unknown>
  also_run_with_model?: string
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

  compareSimulations: async (simulationIds: string[]) => {
    const response = await apiClient.post('/api/simulations/compare', {
      simulation_ids: simulationIds,
    })
    return response.data
  },

  createMultiChemistry: async (params: {
    name_prefix: string
    description?: string
    chemistries: string[]
    c_rate?: number
    temperature_celsius?: number
    cycles?: number
    custom_parameters?: Record<string, unknown>
  }) => {
    const response = await apiClient.post('/api/simulations/multi-chemistry', params)
    return response.data
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

// PyBAMM Reference API - Documentation and model options
export interface PyBAMMModel {
  name: string
  class: string
  description: string
  complexity: string
  recommended_use: string
  variants?: string[]
}

export interface PyBAMMModelOption {
  description: string
  options: (string | number)[]
  default: string
  details?: Record<string, string>
  electrode_specific?: boolean
}

export interface PyBAMMParameterSet {
  chemistry: string
  cell_type: string
  cell_format?: string
  reference: string
}

export interface PyBAMMRecommendation {
  model: string
  options: Record<string, string>
  description: string
}

export const pybammApi = {
  // Get all available PyBAMM models (lithium-ion, lead-acid, ECM)
  getModels: async (): Promise<{
    lithium_ion: Record<string, PyBAMMModel>
    lead_acid: Record<string, PyBAMMModel>
    equivalent_circuit: Record<string, PyBAMMModel>
  }> => {
    const response = await apiClient.get('/api/presets/pybamm/models')
    return response.data
  },

  // Get all available model options (thermal, SEI, lithium plating, etc.)
  getModelOptions: async (): Promise<Record<string, PyBAMMModelOption>> => {
    const response = await apiClient.get('/api/presets/pybamm/options')
    return response.data
  },

  // Get all available parameter sets
  getParameterSets: async (): Promise<Record<string, PyBAMMParameterSet>> => {
    const response = await apiClient.get('/api/presets/pybamm/parameter-sets')
    return response.data
  },

  // Get detailed info about a specific parameter set
  getParameterSetDetails: async (name: string) => {
    const response = await apiClient.get(`/api/presets/pybamm/parameter-sets/${name}`)
    return response.data
  },

  // Get chemistry-specific defaults and info
  getChemistryInfo: async (chemistry: string) => {
    const response = await apiClient.get(`/api/presets/pybamm/chemistry/${chemistry}`)
    return response.data
  },

  // Validate model options
  validateOptions: async (options: Record<string, unknown>): Promise<{
    valid: boolean
    errors: string[]
  }> => {
    const response = await apiClient.post('/api/presets/pybamm/validate-options', options)
    return response.data
  },

  // Get recommended options for a use case
  getRecommendations: async (useCase: string): Promise<PyBAMMRecommendation> => {
    const response = await apiClient.get(`/api/presets/pybamm/recommendations/${useCase}`)
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

// Experiments API - Steps, Templates, and Drive Cycles
export interface ExperimentStepCreate {
  name: string
  description?: string
  is_public?: boolean
  step_type: ExperimentStep['step_type']
  value?: number
  value_unit?: string
  duration?: string
  termination?: string
  period?: string
  temperature?: string
  tags?: string[]
  direction?: 'charge' | 'discharge'
  step_string?: string
  drive_cycle_data?: number[][]
  drive_cycle_type?: 'current' | 'power' | 'voltage'
}

export interface ExperimentStepResponse extends ExperimentStepCreate {
  id: string
  user_id: string | null
  created_at: string
  updated_at: string
}

export interface ExperimentTemplateCreate {
  name: string
  description?: string
  is_public?: boolean
  cycles: ExperimentCycle[]
  default_period?: string
  default_temperature_celsius?: number
}

export interface ExperimentTemplateResponse {
  id: string
  user_id: string | null
  name: string
  description: string | null
  is_public: boolean
  cycles: ExperimentCycle[]
  default_period: string | null
  default_temperature_celsius: number | null
  created_at: string
  updated_at: string
}

export interface DriveCycleCreate {
  name: string
  description?: string
  is_public?: boolean
  cycle_type: 'current' | 'power' | 'voltage'
  data: number[][]
  duration_seconds?: number
  source?: string
  tags?: string[]
}

export interface DriveCycleResponse {
  id: string
  user_id: string | null
  name: string
  description: string | null
  is_public: boolean
  cycle_type: string
  data: number[][]
  duration_seconds: number | null
  source: string | null
  tags: string[] | null
  created_at: string
  updated_at: string
}

export const experimentsApi = {
  // Experiment Steps
  getSteps: async (): Promise<ExperimentStepResponse[]> => {
    const response = await apiClient.get('/api/experiments/steps')
    return response.data
  },

  createStep: async (step: ExperimentStepCreate): Promise<ExperimentStepResponse> => {
    const response = await apiClient.post('/api/experiments/steps', step)
    return response.data
  },

  getStep: async (id: string): Promise<ExperimentStepResponse> => {
    const response = await apiClient.get(`/api/experiments/steps/${id}`)
    return response.data
  },

  deleteStep: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/experiments/steps/${id}`)
  },

  // Experiment Templates
  getTemplates: async (): Promise<ExperimentTemplateResponse[]> => {
    const response = await apiClient.get('/api/experiments/templates')
    return response.data
  },

  createTemplate: async (template: ExperimentTemplateCreate): Promise<ExperimentTemplateResponse> => {
    const response = await apiClient.post('/api/experiments/templates', template)
    return response.data
  },

  getTemplate: async (id: string): Promise<ExperimentTemplateResponse> => {
    const response = await apiClient.get(`/api/experiments/templates/${id}`)
    return response.data
  },

  deleteTemplate: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/experiments/templates/${id}`)
  },

  // Drive Cycles
  getDriveCycles: async (): Promise<DriveCycleResponse[]> => {
    const response = await apiClient.get('/api/experiments/drive-cycles')
    return response.data
  },

  createDriveCycle: async (cycle: DriveCycleCreate): Promise<DriveCycleResponse> => {
    const response = await apiClient.post('/api/experiments/drive-cycles', cycle)
    return response.data
  },

  getDriveCycle: async (id: string): Promise<DriveCycleResponse> => {
    const response = await apiClient.get(`/api/experiments/drive-cycles/${id}`)
    return response.data
  },

  deleteDriveCycle: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/experiments/drive-cycles/${id}`)
  },

  // Validation and Preview
  validateExperiment: async (definition: ExperimentDefinition): Promise<{
    valid: boolean
    errors: string[]
    num_cycles: number
    total_steps: number
  }> => {
    const response = await apiClient.post('/api/experiments/validate', definition)
    return response.data
  },

  previewExperiment: async (definition: ExperimentDefinition): Promise<{
    valid: boolean
    errors: string[]
    preview: { cycle: number; steps: string[] }[] | null
    total_cycles: number
  }> => {
    const response = await apiClient.post('/api/experiments/preview', definition)
    return response.data
  },
}

