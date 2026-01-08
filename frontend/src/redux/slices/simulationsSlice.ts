import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import { simulationsApi } from '../../services/api'

export type SimulationStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
export type BatteryChemistry = 'LFP' | 'NMC' | 'NCA' | 'LCO' | 'custom'

export interface SimulationResults {
  time_seconds: number[]
  voltage_v: number[]
  current_a: number[]
  discharge_capacity_ah?: number[]
  summary: {
    max_voltage: number
    min_voltage: number
    total_time_hours: number
    chemistry: string
    c_rate: number
    temperature_celsius: number
    cycles: number
    total_capacity_ah?: number
  }
}

export interface Simulation {
  id: string
  user_id: string
  name: string
  description: string | null
  status: SimulationStatus
  progress: number
  chemistry: BatteryChemistry
  c_rate: number
  temperature_celsius: number
  cycles: number
  custom_parameters: Record<string, unknown> | null
  results: SimulationResults | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface CreateSimulationParams {
  name: string
  description?: string
  chemistry?: BatteryChemistry
  c_rate?: number
  temperature_celsius?: number
  cycles?: number
  custom_parameters?: Record<string, unknown>
}

interface SimulationsState {
  simulations: Simulation[]
  currentSimulation: Simulation | null
  loading: boolean
  error: string | null
  pollingId: string | null
}

const initialState: SimulationsState = {
  simulations: [],
  currentSimulation: null,
  loading: false,
  error: null,
  pollingId: null,
}

export const fetchSimulations = createAsyncThunk(
  'simulations/fetchAll',
  async (_, { rejectWithValue }) => {
    try {
      return await simulationsApi.getSimulations()
    } catch (error: unknown) {
      const err = error as { message?: string }
      return rejectWithValue(err.message || 'Failed to fetch simulations')
    }
  }
)

export const fetchSimulation = createAsyncThunk(
  'simulations/fetchOne',
  async (id: string, { rejectWithValue }) => {
    try {
      return await simulationsApi.getSimulation(id)
    } catch (error: unknown) {
      const err = error as { message?: string }
      return rejectWithValue(err.message || 'Failed to fetch simulation')
    }
  }
)

export const createSimulation = createAsyncThunk(
  'simulations/create',
  async (params: CreateSimulationParams, { rejectWithValue }) => {
    try {
      return await simulationsApi.createSimulation(params)
    } catch (error: unknown) {
      const err = error as { message?: string }
      return rejectWithValue(err.message || 'Failed to create simulation')
    }
  }
)

export const deleteSimulation = createAsyncThunk(
  'simulations/delete',
  async (id: string, { rejectWithValue }) => {
    try {
      await simulationsApi.deleteSimulation(id)
      return id
    } catch (error: unknown) {
      const err = error as { message?: string }
      return rejectWithValue(err.message || 'Failed to delete simulation')
    }
  }
)

export const cancelSimulation = createAsyncThunk(
  'simulations/cancel',
  async (id: string, { rejectWithValue }) => {
    try {
      await simulationsApi.cancelSimulation(id)
      return id
    } catch (error: unknown) {
      const err = error as { message?: string }
      return rejectWithValue(err.message || 'Failed to cancel simulation')
    }
  }
)

const simulationsSlice = createSlice({
  name: 'simulations',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null
    },
    setCurrentSimulation: (state, action: PayloadAction<Simulation | null>) => {
      state.currentSimulation = action.payload
    },
    updateSimulationInList: (state, action: PayloadAction<Simulation>) => {
      const index = state.simulations.findIndex(s => s.id === action.payload.id)
      if (index !== -1) {
        state.simulations[index] = action.payload
      }
      if (state.currentSimulation?.id === action.payload.id) {
        state.currentSimulation = action.payload
      }
    },
    setPollingId: (state, action: PayloadAction<string | null>) => {
      state.pollingId = action.payload
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch all simulations
      .addCase(fetchSimulations.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchSimulations.fulfilled, (state, action) => {
        state.loading = false
        state.simulations = action.payload
      })
      .addCase(fetchSimulations.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload as string
      })
      // Fetch single simulation
      .addCase(fetchSimulation.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchSimulation.fulfilled, (state, action) => {
        state.loading = false
        state.currentSimulation = action.payload
        const index = state.simulations.findIndex(s => s.id === action.payload.id)
        if (index !== -1) {
          state.simulations[index] = action.payload
        }
      })
      .addCase(fetchSimulation.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload as string
      })
      // Create simulation
      .addCase(createSimulation.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(createSimulation.fulfilled, (state, action) => {
        state.loading = false
        state.simulations.unshift(action.payload)
        state.currentSimulation = action.payload
      })
      .addCase(createSimulation.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload as string
      })
      // Delete simulation
      .addCase(deleteSimulation.fulfilled, (state, action) => {
        state.simulations = state.simulations.filter(s => s.id !== action.payload)
        if (state.currentSimulation?.id === action.payload) {
          state.currentSimulation = null
        }
      })
      // Cancel simulation
      .addCase(cancelSimulation.fulfilled, (state, action) => {
        const index = state.simulations.findIndex(s => s.id === action.payload)
        if (index !== -1) {
          state.simulations[index].status = 'cancelled'
        }
        if (state.currentSimulation?.id === action.payload) {
          state.currentSimulation.status = 'cancelled'
        }
      })
  },
})

export const { clearError, setCurrentSimulation, updateSimulationInList, setPollingId } = simulationsSlice.actions
export default simulationsSlice.reducer
