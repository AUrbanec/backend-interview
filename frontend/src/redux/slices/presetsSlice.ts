import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { presetsApi } from '../../services/api'
import { BatteryChemistry } from './simulationsSlice'

export interface Preset {
  id: string
  user_id: string | null
  name: string
  description: string | null
  is_public: boolean
  chemistry: BatteryChemistry
  c_rate: number
  temperature_celsius: number
  cycles: number
  custom_parameters: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface CreatePresetParams {
  name: string
  description?: string
  is_public?: boolean
  chemistry?: BatteryChemistry
  c_rate?: number
  temperature_celsius?: number
  cycles?: number
  custom_parameters?: Record<string, unknown>
}

export interface UpdatePresetParams {
  name?: string
  description?: string
  is_public?: boolean
  chemistry?: BatteryChemistry
  c_rate?: number
  temperature_celsius?: number
  cycles?: number
  custom_parameters?: Record<string, unknown>
}

interface PresetsState {
  presets: Preset[]
  loading: boolean
  error: string | null
}

const initialState: PresetsState = {
  presets: [],
  loading: false,
  error: null,
}

export const fetchPresets = createAsyncThunk(
  'presets/fetchAll',
  async (_, { rejectWithValue }) => {
    try {
      return await presetsApi.getPresets()
    } catch (error: unknown) {
      const err = error as { message?: string }
      return rejectWithValue(err.message || 'Failed to fetch presets')
    }
  }
)

export const createPreset = createAsyncThunk(
  'presets/create',
  async (params: CreatePresetParams, { rejectWithValue }) => {
    try {
      return await presetsApi.createPreset(params)
    } catch (error: unknown) {
      const err = error as { message?: string }
      return rejectWithValue(err.message || 'Failed to create preset')
    }
  }
)

export const updatePreset = createAsyncThunk(
  'presets/update',
  async ({ id, updates }: { id: string; updates: UpdatePresetParams }, { rejectWithValue }) => {
    try {
      return await presetsApi.updatePreset(id, updates)
    } catch (error: unknown) {
      const err = error as { message?: string }
      return rejectWithValue(err.message || 'Failed to update preset')
    }
  }
)

export const deletePreset = createAsyncThunk(
  'presets/delete',
  async (id: string, { rejectWithValue }) => {
    try {
      await presetsApi.deletePreset(id)
      return id
    } catch (error: unknown) {
      const err = error as { message?: string }
      return rejectWithValue(err.message || 'Failed to delete preset')
    }
  }
)

export const duplicatePreset = createAsyncThunk(
  'presets/duplicate',
  async ({ id, newName }: { id: string; newName?: string }, { rejectWithValue }) => {
    try {
      return await presetsApi.duplicatePreset(id, newName)
    } catch (error: unknown) {
      const err = error as { message?: string }
      return rejectWithValue(err.message || 'Failed to duplicate preset')
    }
  }
)

const presetsSlice = createSlice({
  name: 'presets',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchPresets.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchPresets.fulfilled, (state, action) => {
        state.loading = false
        state.presets = action.payload
      })
      .addCase(fetchPresets.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload as string
      })
      .addCase(createPreset.fulfilled, (state, action) => {
        state.presets.push(action.payload)
      })
      .addCase(updatePreset.fulfilled, (state, action) => {
        const index = state.presets.findIndex(p => p.id === action.payload.id)
        if (index !== -1) {
          state.presets[index] = action.payload
        }
      })
      .addCase(deletePreset.fulfilled, (state, action) => {
        state.presets = state.presets.filter(p => p.id !== action.payload)
      })
      .addCase(duplicatePreset.fulfilled, (state, action) => {
        state.presets.push(action.payload)
      })
  },
})

export const { clearError } = presetsSlice.actions
export default presetsSlice.reducer
