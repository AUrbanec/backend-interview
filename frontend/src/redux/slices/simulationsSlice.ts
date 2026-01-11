import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import { simulationsApi } from '../../services/api'

export type SimulationStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
export type BatteryChemistry = 'LFP' | 'NMC' | 'NCA' | 'LCO' | 'SODIUM_ION' | 'LEAD_ACID' | 'custom'
export type ParameterSet = 'Chen2020' | 'ORegan2022' | 'Ai2020' | 'Mohtat2020' | 'Prada2013' | 'NCA_Kim2011' | 'Marquis2019' | 'Ecker2015' | 'Ramadass2004' | 'Xu2019' | 'Chayambuka2022' | 'custom'
export type ProtocolType = 'standard_cycle' | 'capacity_check' | 'rate_capability' | 'drive_cycle' | 'hppc' | 'custom'
export type ModelType = 'SPM' | 'SPMe' | 'DFN' | 'MPM' | 'NewmanTobias'
export type ExperimentMode = 'protocol' | 'custom' | 'template'
export type StepType = 'current' | 'c_rate' | 'voltage' | 'power' | 'resistance' | 'rest' | 'string'

export interface StepMetric {
  step_number: number
  start_index: number
  end_index: number
  duration_seconds: number
  average_current_a: number
  start_voltage_v: number | null
  end_voltage_v: number | null
  delivered_ah: number
  delivered_wh: number
}

export type ThermalMode = 'isothermal' | 'lumped'

// Experiment step and cycle types
export interface ExperimentStep {
  step_type: StepType
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

export interface SafetyEvent {
  type: string
  message: string
  severity: 'warning' | 'critical'
}

export interface ThermalThresholds {
  max_temp_warning_celsius: number
  max_temp_critical_celsius: number
  min_temp_warning_celsius: number
  min_temp_critical_celsius: number
}

export interface SimulationResults {
  time_seconds: number[]
  voltage_v: number[]
  current_a: number[]
  discharge_capacity_ah?: number[]
  soc?: number[]
  temperature_celsius?: number[]
  power_w?: number[]
  heat_generation_w_m3?: number[]
  positive_electrode_potential_v?: number[]
  negative_electrode_potential_v?: number[]
  protocol?: {
    protocol_type: ProtocolType
    voltage_limits: {
      lower_voltage_cutoff: number
      upper_voltage_cutoff: number
      nominal_voltage: number
    }
    cycles: number
  }
  step_boundaries?: { start_index: number; end_index: number }[]
  step_metrics?: StepMetric[]
  summary: {
    max_voltage: number
    min_voltage: number
    total_time_hours: number
    chemistry: string
    c_rate: number
    temperature_celsius: number
    cycles: number
    total_capacity_ah?: number
    protocol_type?: ProtocolType
    num_steps?: number
    total_delivered_ah?: number
    total_delivered_wh?: number
    initial_soc?: number
    final_soc?: number
    max_temperature_celsius?: number
    min_temperature_celsius?: number
    avg_temperature_celsius?: number
    max_power_w?: number
    min_power_w?: number
    avg_power_w?: number
    // Thermal safety fields
    thermal_mode?: ThermalMode
    time_above_warning_seconds?: number
    time_above_critical_seconds?: number
    time_below_cold_warning_seconds?: number
    time_below_cold_critical_seconds?: number
    max_heat_generation_w_m3?: number
    avg_heat_generation_w_m3?: number
    // Safety flags
    max_temp_exceeded?: boolean
    voltage_violation?: boolean
    safety_events?: SafetyEvent[]
    thermal_thresholds?: ThermalThresholds
  }
}

export interface Simulation {
  id: string
  user_id: string
  name: string
  description: string | null
  status: SimulationStatus
  progress: number
  // Cell & Model
  parameter_set: ParameterSet | null
  chemistry: BatteryChemistry
  model_type: ModelType | null
  model_options: Record<string, string> | null
  // Experiment
  protocol: ProtocolType | null
  c_rate: number
  temperature_celsius: number
  cycles: number
  experiment_mode: ExperimentMode | null
  experiment_definition: ExperimentDefinition | null
  experiment_template_id: string | null
  experiment_period: string | null
  // Additional
  custom_parameters: Record<string, unknown> | null
  also_run_with_model: ModelType | null
  comparison_simulation_id: string | null
  // Results and status
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
  // Cell & Model
  parameter_set?: ParameterSet | string
  chemistry?: BatteryChemistry
  model_type?: ModelType
  model_options?: Record<string, string>
  // Experiment
  protocol?: ProtocolType
  c_rate?: number
  temperature_celsius?: number
  cycles?: number
  experiment_mode?: ExperimentMode
  experiment_definition?: ExperimentDefinition
  experiment_template_id?: string
  experiment_period?: string
  // Additional
  custom_parameters?: Record<string, unknown>
  also_run_with_model?: ModelType
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
