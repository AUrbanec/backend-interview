import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Stepper,
  Step,
  StepLabel,
  Typography,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Paper,
  Chip,
  Grid,
  FormControlLabel,
  Checkbox,
  Divider,
  CircularProgress,
} from '@mui/material'
import {
  BatteryFull as BatteryIcon,
  Science as ModelIcon,
  PlayArrow as RunIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material'
import ParameterSetSelector, { ParameterSetInfo } from './ParameterSetSelector'
import ExperimentSelector, { ProtocolType, ExperimentMode } from './ExperimentSelector'
import AdvancedModelOptions, { ModelType, ModelOptions } from './AdvancedModelOptions'
import { ExperimentDefinition, ExperimentTemplateResponse, experimentsApi } from '../services/api'

const STEPS = ['Cell & Model', 'Experiment', 'Review & Run']

export type { ModelType } from './AdvancedModelOptions'

export interface SimulationWizardData {
  name: string
  description: string
  // Step 1: Cell & Model
  parameterSet: string | null
  parameterSetInfo: ParameterSetInfo | null
  chemistry: string
  modelType: ModelType
  modelOptions: ModelOptions
  // Step 2: Experiment
  protocol: ProtocolType
  cRate: number
  temperatureCelsius: number
  cycles: number
  experimentMode: ExperimentMode
  experimentDefinition: ExperimentDefinition | null
  experimentTemplateId: string
  // Step 3: Review
  alsoRunWithModel: ModelType | null
}

interface SimulationWizardProps {
  open: boolean
  onClose: () => void
  onSubmit: (data: SimulationWizardData) => void
  loading?: boolean
}

const MODEL_TYPE_INFO: Record<ModelType, { label: string; description: string; speed: string }> = {
  SPM: { label: 'SPM', description: 'Single Particle Model', speed: 'Fastest' },
  SPMe: { label: 'SPMe', description: 'SPM with Electrolyte', speed: 'Fast' },
  DFN: { label: 'DFN', description: 'Doyle-Fuller-Newman', speed: 'Accurate' },
  MPM: { label: 'MPM', description: 'Many Particle Model', speed: 'Slow' },
  NewmanTobias: { label: 'Newman-Tobias', description: 'Simplified DFN', speed: 'Medium' },
}

const SimulationWizard = ({ open, onClose, onSubmit, loading = false }: SimulationWizardProps) => {
  const [activeStep, setActiveStep] = useState(0)
  const [templates, setTemplates] = useState<ExperimentTemplateResponse[]>([])
  const [showAdvancedModel, setShowAdvancedModel] = useState(false)

  // Form state
  const [data, setData] = useState<SimulationWizardData>({
    name: '',
    description: '',
    parameterSet: null,
    parameterSetInfo: null,
    chemistry: 'NMC',
    modelType: 'DFN',
    modelOptions: {},
    protocol: 'standard_cycle',
    cRate: 1.0,
    temperatureCelsius: 25,
    cycles: 1,
    experimentMode: 'protocol',
    experimentDefinition: null,
    experimentTemplateId: '',
    alsoRunWithModel: null,
  })

  useEffect(() => {
    if (open) {
      loadTemplates()
    }
  }, [open])

  const loadTemplates = async () => {
    try {
      const result = await experimentsApi.getTemplates()
      setTemplates(result)
    } catch (err) {
      console.error('Failed to load templates:', err)
    }
  }

  const updateData = (updates: Partial<SimulationWizardData>) => {
    setData(prev => ({ ...prev, ...updates }))
  }

  const handleParameterSetChange = (parameterSet: string, info: ParameterSetInfo) => {
    updateData({
      parameterSet,
      parameterSetInfo: info,
      chemistry: info.chemistry,
    })
  }

  const handleNext = () => {
    if (activeStep === STEPS.length - 1) {
      // Auto-generate name if empty
      const finalData = { ...data }
      if (!finalData.name.trim()) {
        const paramSetName = finalData.parameterSet || finalData.chemistry
        const protocolName = finalData.protocol.replace(/_/g, ' ')
        finalData.name = `${paramSetName} - ${protocolName} @ ${finalData.temperatureCelsius}°C`
      }
      onSubmit(finalData)
    } else {
      setActiveStep(prev => prev + 1)
    }
  }

  const handleBack = () => {
    setActiveStep(prev => prev - 1)
  }

  const canProceed = () => {
    switch (activeStep) {
      case 0:
        // Must have a parameter set or chemistry selected
        return data.parameterSet || data.chemistry
      case 1:
        // Must have valid experiment settings
        if (data.experimentMode === 'custom') {
          return data.experimentDefinition && data.experimentDefinition.cycles.length > 0
        }
        return true
      case 2:
        // Review step - always can proceed
        return true
      default:
        return false
    }
  }

  const getEstimatedRuntime = () => {
    // Simple estimation based on model type and cycles
    const baseTime = {
      SPM: 5,
      SPMe: 15,
      DFN: 60,
      MPM: 120,
      NewmanTobias: 30,
    }[data.modelType] || 60

    const cycleMultiplier = data.cycles
    const estimated = baseTime * cycleMultiplier
    
    if (estimated < 60) return `~${estimated} seconds`
    if (estimated < 3600) return `~${Math.round(estimated / 60)} minutes`
    return `~${(estimated / 3600).toFixed(1)} hours`
  }

  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        return (
          <Box>
            {/* Parameter Set Selection */}
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <BatteryIcon /> Select Cell Parameter Set
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Choose a validated PyBaMM parameter set for your simulation. These contain experimentally
              measured parameters for specific battery cells.
            </Typography>

            <ParameterSetSelector
              value={data.parameterSet}
              onChange={handleParameterSetChange}
            />

            <Divider sx={{ my: 3 }} />

            {/* Model Selection */}
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ModelIcon /> Select Model Fidelity
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Choose the electrochemical model complexity. Higher fidelity models are more accurate
              but take longer to simulate.
            </Typography>

            <Grid container spacing={2} sx={{ mb: 2 }}>
              {(Object.entries(MODEL_TYPE_INFO) as [ModelType, typeof MODEL_TYPE_INFO[ModelType]][]).map(([type, info]) => (
                <Grid item xs={6} sm={4} md={2.4} key={type}>
                  <Paper
                    variant={data.modelType === type ? 'elevation' : 'outlined'}
                    sx={{
                      p: 2,
                      cursor: 'pointer',
                      border: data.modelType === type ? '2px solid' : undefined,
                      borderColor: data.modelType === type ? 'primary.main' : undefined,
                      textAlign: 'center',
                      '&:hover': { bgcolor: 'action.hover' },
                    }}
                    onClick={() => updateData({ modelType: type })}
                  >
                    <Typography variant="subtitle1" fontWeight="bold">
                      {info.label}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" display="block">
                      {info.description}
                    </Typography>
                    <Chip
                      label={info.speed}
                      size="small"
                      color={info.speed === 'Fastest' ? 'success' : info.speed === 'Fast' ? 'info' : 'default'}
                      sx={{ mt: 1 }}
                    />
                  </Paper>
                </Grid>
              ))}
            </Grid>

            {/* Advanced Model Options */}
            <Button
              size="small"
              onClick={() => setShowAdvancedModel(!showAdvancedModel)}
              sx={{ mb: 1 }}
            >
              {showAdvancedModel ? 'Hide' : 'Show'} Advanced Model Options
            </Button>
            {showAdvancedModel && (
              <Box sx={{ mt: 1 }}>
                <AdvancedModelOptions
                  modelType={data.modelType}
                  modelOptions={data.modelOptions}
                  onModelTypeChange={(type) => updateData({ modelType: type })}
                  onModelOptionsChange={(options) => updateData({ modelOptions: options })}
                  expanded={true}
                />
              </Box>
            )}
          </Box>
        )

      case 1:
        return (
          <Box>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <SpeedIcon /> Configure Experiment
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Select a standard test protocol or build a custom experiment with precise control
              over charge/discharge steps.
            </Typography>

            <ExperimentSelector
              protocol={data.protocol}
              cRate={data.cRate}
              temperatureCelsius={data.temperatureCelsius}
              cycles={data.cycles}
              experimentMode={data.experimentMode}
              experimentDefinition={data.experimentDefinition}
              experimentTemplateId={data.experimentTemplateId}
              templates={templates}
              onProtocolChange={(p) => updateData({ protocol: p })}
              onCRateChange={(c) => updateData({ cRate: c })}
              onTemperatureChange={(t) => updateData({ temperatureCelsius: t })}
              onCyclesChange={(c) => updateData({ cycles: c })}
              onExperimentModeChange={(m) => updateData({ experimentMode: m })}
              onExperimentDefinitionChange={(d) => updateData({ experimentDefinition: d })}
              onTemplateIdChange={(id) => updateData({ experimentTemplateId: id })}
            />
          </Box>
        )

      case 2:
        return (
          <Box>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <RunIcon /> Review & Run
            </Typography>

            {/* Name and Description */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Simulation Name"
                  placeholder="Auto-generated if left blank"
                  value={data.name}
                  onChange={(e) => updateData({ name: e.target.value })}
                  helperText={!data.name && `Default: ${data.parameterSet || data.chemistry} - ${data.protocol.replace(/_/g, ' ')} @ ${data.temperatureCelsius}°C`}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Description (optional)"
                  multiline
                  rows={2}
                  value={data.description}
                  onChange={(e) => updateData({ description: e.target.value })}
                />
              </Grid>
            </Grid>

            {/* Summary */}
            <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Simulation Summary
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Typography variant="body2">
                    <strong>Cell:</strong> {data.parameterSetInfo?.full_name || data.parameterSet || data.chemistry}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Chemistry:</strong> {data.chemistry}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Model:</strong> {MODEL_TYPE_INFO[data.modelType].label} ({MODEL_TYPE_INFO[data.modelType].description})
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="body2">
                    <strong>Experiment:</strong> {data.protocol.replace(/_/g, ' ')}
                  </Typography>
                  <Typography variant="body2">
                    <strong>C-Rate:</strong> {data.cRate < 1 ? `C/${Math.round(1/data.cRate)}` : `${data.cRate}C`}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Temperature:</strong> {data.temperatureCelsius}°C
                  </Typography>
                  <Typography variant="body2">
                    <strong>Cycles:</strong> {data.cycles}
                  </Typography>
                </Grid>
              </Grid>
              <Divider sx={{ my: 2 }} />
              <Typography variant="body2" color="text.secondary">
                <strong>Estimated runtime:</strong> {getEstimatedRuntime()}
              </Typography>
            </Paper>

            {/* Comparison Option */}
            <Paper variant="outlined" sx={{ p: 2 }}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={data.alsoRunWithModel !== null}
                    onChange={(e) => {
                      if (e.target.checked) {
                        // Default to SPM for comparison if using DFN, otherwise DFN
                        updateData({ alsoRunWithModel: data.modelType === 'DFN' ? 'SPM' : 'DFN' })
                      } else {
                        updateData({ alsoRunWithModel: null })
                      }
                    }}
                  />
                }
                label="Also run with different model for comparison"
              />
              {data.alsoRunWithModel && (
                <FormControl size="small" sx={{ ml: 4, minWidth: 150 }}>
                  <InputLabel>Compare with</InputLabel>
                  <Select
                    value={data.alsoRunWithModel}
                    label="Compare with"
                    onChange={(e) => updateData({ alsoRunWithModel: e.target.value as ModelType })}
                  >
                    {(Object.keys(MODEL_TYPE_INFO) as ModelType[])
                      .filter(t => t !== data.modelType)
                      .map(type => (
                        <MenuItem key={type} value={type}>
                          {MODEL_TYPE_INFO[type].label}
                        </MenuItem>
                      ))}
                  </Select>
                </FormControl>
              )}
              {data.alsoRunWithModel && (
                <Alert severity="info" sx={{ mt: 1 }}>
                  Two simulations will be created: one with {data.modelType} and one with {data.alsoRunWithModel}.
                  You can compare them in the Results Viewer.
                </Alert>
              )}
            </Paper>
          </Box>
        )

      default:
        return null
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{ sx: { minHeight: '80vh' } }}
    >
      <DialogTitle>
        <Typography variant="h5">Create New Simulation</Typography>
      </DialogTitle>

      <DialogContent dividers>
        {/* Stepper */}
        <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
          {STEPS.map((label, index) => (
            <Step key={label} completed={index < activeStep}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {/* Step Content */}
        {renderStepContent()}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Box sx={{ flex: 1 }} />
        {activeStep > 0 && (
          <Button onClick={handleBack} disabled={loading}>
            Back
          </Button>
        )}
        <Button
          variant="contained"
          onClick={handleNext}
          disabled={!canProceed() || loading}
          startIcon={loading ? <CircularProgress size={20} /> : activeStep === STEPS.length - 1 ? <RunIcon /> : undefined}
        >
          {activeStep === STEPS.length - 1 ? (loading ? 'Creating...' : 'Run Simulation') : 'Next'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default SimulationWizard
