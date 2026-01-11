import { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  Tooltip,
  Divider,
  Card,
  CardContent,
} from '@mui/material'
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  ContentCopy as CopyIcon,
  ArrowUpward as MoveUpIcon,
  ArrowDownward as MoveDownIcon,
  PlayArrow as PreviewIcon,
} from '@mui/icons-material'
import {
  ExperimentDefinition,
  ExperimentCycle,
  ExperimentStep,
  StepType,
} from '../redux/slices/simulationsSlice'
import { experimentsApi, ExperimentTemplateResponse } from '../services/api'

interface ExperimentBuilderProps {
  value: ExperimentDefinition | null
  onChange: (definition: ExperimentDefinition) => void
  templates?: ExperimentTemplateResponse[]
}

const STEP_TYPES: { value: StepType; label: string; description: string }[] = [
  { value: 'string', label: 'String Command', description: 'Raw PyBAMM instruction string' },
  { value: 'current', label: 'Current', description: 'Constant current step (A)' },
  { value: 'c_rate', label: 'C-Rate', description: 'Current as C-rate multiplier' },
  { value: 'voltage', label: 'Voltage', description: 'Constant voltage step (V)' },
  { value: 'power', label: 'Power', description: 'Constant power step (W)' },
  { value: 'rest', label: 'Rest', description: 'Open circuit rest period' },
  { value: 'resistance', label: 'Resistance', description: 'Constant resistance step (Ω)' },
]

const DEFAULT_STEP: ExperimentStep = {
  step_type: 'string',
  step_string: 'Discharge at 1C until 3.0V',
}

const DEFAULT_CYCLE: ExperimentCycle = {
  steps: [{ ...DEFAULT_STEP }],
  repeat: 1,
}

// Quick step presets for common operations
const QUICK_STEPS: { label: string; step: ExperimentStep }[] = [
  { label: 'Charge 1C', step: { step_type: 'string', step_string: 'Charge at 1C until 4.2V' } },
  { label: 'Charge C/2', step: { step_type: 'string', step_string: 'Charge at C/2 until 4.2V' } },
  { label: 'Discharge 1C', step: { step_type: 'string', step_string: 'Discharge at 1C until 3.0V' } },
  { label: 'Discharge C/2', step: { step_type: 'string', step_string: 'Discharge at C/2 until 3.0V' } },
  { label: 'CV Hold', step: { step_type: 'string', step_string: 'Hold at 4.2V until C/20' } },
  { label: 'Rest 10min', step: { step_type: 'string', step_string: 'Rest for 10 minutes' } },
  { label: 'Rest 1hr', step: { step_type: 'string', step_string: 'Rest for 1 hour' } },
  { label: 'CCCV Charge', step: { step_type: 'string', step_string: 'Charge at 1C until 4.2V, Hold at 4.2V until C/20' } },
]

const ExperimentBuilder = ({ value, onChange, templates = [] }: ExperimentBuilderProps) => {
  const [definition, setDefinition] = useState<ExperimentDefinition>(() => {
    // Initialize with value or default
    return value || {
      cycles: [{ ...DEFAULT_CYCLE }],
      default_period: '1 minute',
      default_temperature_celsius: 25.0,
    }
  })
  const [previewResult, setPreviewResult] = useState<{
    valid: boolean
    errors: string[]
    preview: { cycle: number; steps: string[] }[] | null
    total_cycles?: number
  } | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  // Sync when value changes from parent
  useEffect(() => {
    if (value) {
      setDefinition(value)
    }
  }, [value])

  // Notify parent of changes
  useEffect(() => {
    onChange(definition)
  }, [definition]) // eslint-disable-line react-hooks/exhaustive-deps

  const updateDefinition = (updates: Partial<ExperimentDefinition>) => {
    setDefinition(prev => ({ ...prev, ...updates }))
    setPreviewResult(null)
  }

  const addCycle = () => {
    updateDefinition({
      cycles: [...definition.cycles, { ...DEFAULT_CYCLE, steps: [{ ...DEFAULT_STEP }] }],
    })
  }

  const removeCycle = (cycleIndex: number) => {
    if (definition.cycles.length <= 1) return
    updateDefinition({
      cycles: definition.cycles.filter((_, i) => i !== cycleIndex),
    })
  }

  const updateCycle = (cycleIndex: number, updates: Partial<ExperimentCycle>) => {
    updateDefinition({
      cycles: definition.cycles.map((cycle, i) =>
        i === cycleIndex ? { ...cycle, ...updates } : cycle
      ),
    })
  }

  const moveCycle = (cycleIndex: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? cycleIndex - 1 : cycleIndex + 1
    if (newIndex < 0 || newIndex >= definition.cycles.length) return
    const newCycles = [...definition.cycles]
    ;[newCycles[cycleIndex], newCycles[newIndex]] = [newCycles[newIndex], newCycles[cycleIndex]]
    updateDefinition({ cycles: newCycles })
  }

  const duplicateCycle = (cycleIndex: number) => {
    const cycleToCopy = definition.cycles[cycleIndex]
    const newCycle = {
      ...cycleToCopy,
      steps: cycleToCopy.steps.map(s => ({ ...s })),
    }
    const newCycles = [...definition.cycles]
    newCycles.splice(cycleIndex + 1, 0, newCycle)
    updateDefinition({ cycles: newCycles })
  }

  const addStep = (cycleIndex: number) => {
    updateCycle(cycleIndex, {
      steps: [...definition.cycles[cycleIndex].steps, { ...DEFAULT_STEP }],
    })
  }

  const removeStep = (cycleIndex: number, stepIndex: number) => {
    const cycle = definition.cycles[cycleIndex]
    if (cycle.steps.length <= 1) return
    updateCycle(cycleIndex, {
      steps: cycle.steps.filter((_, i) => i !== stepIndex),
    })
  }

  const updateStep = (cycleIndex: number, stepIndex: number, updates: Partial<ExperimentStep>) => {
    const cycle = definition.cycles[cycleIndex]
    updateCycle(cycleIndex, {
      steps: cycle.steps.map((step, i) =>
        i === stepIndex ? { ...step, ...updates } : step
      ),
    })
  }

  const handlePreview = async () => {
    setPreviewLoading(true)
    try {
      const result = await experimentsApi.previewExperiment(definition)
      setPreviewResult(result)
    } catch (error) {
      setPreviewResult({
        valid: false,
        errors: [(error as Error).message || 'Preview failed'],
        preview: null,
      })
    } finally {
      setPreviewLoading(false)
    }
  }

  const loadTemplate = (template: ExperimentTemplateResponse) => {
    setDefinition({
      cycles: template.cycles.map(c => ({
        steps: c.steps.map((s: ExperimentStep) => ({ ...s })),
        repeat: c.repeat || 1,
      })),
      default_period: template.default_period || '1 minute',
      default_temperature_celsius: template.default_temperature_celsius || 25.0,
    })
    setPreviewResult(null)
  }

  const renderStepEditor = (step: ExperimentStep, cycleIndex: number, stepIndex: number) => {
    const isStringType = step.step_type === 'string'
    const isRestType = step.step_type === 'rest'

    return (
      <Card variant="outlined" sx={{ mb: 1 }}>
        <CardContent sx={{ pb: 1 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Step Type</InputLabel>
                <Select
                  value={step.step_type}
                  label="Step Type"
                  onChange={(e) => updateStep(cycleIndex, stepIndex, {
                    step_type: e.target.value as StepType,
                    value: undefined,
                    step_string: e.target.value === 'string' ? 'Discharge at 1C until 3.0V' : undefined,
                  })}
                >
                  {STEP_TYPES.map((type) => (
                    <MenuItem key={type.value} value={type.value}>
                      <Tooltip title={type.description} placement="right">
                        <span>{type.label}</span>
                      </Tooltip>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            {isStringType ? (
              <Grid item xs={12} sm={7}>
                <TextField
                  fullWidth
                  size="small"
                  label="PyBAMM Command"
                  placeholder="e.g., Discharge at 1C until 3.0V"
                  value={step.step_string || ''}
                  onChange={(e) => updateStep(cycleIndex, stepIndex, { step_string: e.target.value })}
                  helperText="Enter a PyBAMM experiment string"
                />
              </Grid>
            ) : isRestType ? (
              <Grid item xs={12} sm={7}>
                <TextField
                  fullWidth
                  size="small"
                  label="Duration"
                  placeholder="e.g., 10 minutes, 1 hour"
                  value={step.duration || ''}
                  onChange={(e) => updateStep(cycleIndex, stepIndex, { duration: e.target.value })}
                />
              </Grid>
            ) : (
              <>
                <Grid item xs={6} sm={2}>
                  <TextField
                    fullWidth
                    size="small"
                    type="number"
                    label="Value"
                    value={step.value || ''}
                    onChange={(e) => updateStep(cycleIndex, stepIndex, { value: parseFloat(e.target.value) || undefined })}
                  />
                </Grid>
                <Grid item xs={6} sm={2}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Duration"
                    placeholder="1 hour"
                    value={step.duration || ''}
                    onChange={(e) => updateStep(cycleIndex, stepIndex, { duration: e.target.value })}
                  />
                </Grid>
                <Grid item xs={12} sm={3}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Termination"
                    placeholder="3.0V, C/50"
                    value={step.termination || ''}
                    onChange={(e) => updateStep(cycleIndex, stepIndex, { termination: e.target.value })}
                  />
                </Grid>
              </>
            )}

            <Grid item xs={12} sm={2}>
              <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                <IconButton
                  size="small"
                  color="error"
                  onClick={() => removeStep(cycleIndex, stepIndex)}
                  disabled={definition.cycles[cycleIndex].steps.length <= 1}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    )
  }

  return (
    <Box>
      {/* Templates Section */}
      {templates.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Load from Template:
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {templates.map((template) => (
              <Chip
                key={template.id}
                label={template.name}
                onClick={() => loadTemplate(template)}
                variant="outlined"
                clickable
                size="small"
              />
            ))}
          </Box>
        </Box>
      )}

      {/* Default Settings */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Default Settings
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={6}>
            <TextField
              fullWidth
              size="small"
              label="Default Period"
              value={definition.default_period || '1 minute'}
              onChange={(e) => updateDefinition({ default_period: e.target.value })}
              helperText="Sampling period for steps"
            />
          </Grid>
          <Grid item xs={6}>
            <TextField
              fullWidth
              size="small"
              type="number"
              label="Default Temperature (°C)"
              value={definition.default_temperature_celsius || 25}
              onChange={(e) => updateDefinition({ default_temperature_celsius: parseFloat(e.target.value) || 25 })}
            />
          </Grid>
        </Grid>
      </Paper>

      {/* Cycles */}
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle1">
            Experiment Cycles ({definition.cycles.length})
          </Typography>
          <Button startIcon={<AddIcon />} size="small" onClick={addCycle}>
            Add Cycle
          </Button>
        </Box>

        {definition.cycles.map((cycle, cycleIndex) => (
          <Accordion key={cycleIndex} defaultExpanded={cycleIndex === 0}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%', pr: 2 }}>
                <Typography variant="subtitle2">
                  Cycle {cycleIndex + 1}
                </Typography>
                <Chip
                  label={`${cycle.steps.length} steps`}
                  size="small"
                  variant="outlined"
                />
                {cycle.repeat > 1 && (
                  <Chip
                    label={`×${cycle.repeat}`}
                    size="small"
                    color="primary"
                  />
                )}
                <Box sx={{ flexGrow: 1 }} />
                <IconButton
                  size="small"
                  onClick={(e) => { e.stopPropagation(); moveCycle(cycleIndex, 'up') }}
                  disabled={cycleIndex === 0}
                >
                  <MoveUpIcon fontSize="small" />
                </IconButton>
                <IconButton
                  size="small"
                  onClick={(e) => { e.stopPropagation(); moveCycle(cycleIndex, 'down') }}
                  disabled={cycleIndex === definition.cycles.length - 1}
                >
                  <MoveDownIcon fontSize="small" />
                </IconButton>
                <IconButton
                  size="small"
                  onClick={(e) => { e.stopPropagation(); duplicateCycle(cycleIndex) }}
                >
                  <CopyIcon fontSize="small" />
                </IconButton>
                <IconButton
                  size="small"
                  color="error"
                  onClick={(e) => { e.stopPropagation(); removeCycle(cycleIndex) }}
                  disabled={definition.cycles.length <= 1}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Box sx={{ mb: 2 }}>
                <TextField
                  size="small"
                  type="number"
                  label="Repeat Count"
                  value={cycle.repeat}
                  onChange={(e) => updateCycle(cycleIndex, { repeat: Math.max(1, parseInt(e.target.value) || 1) })}
                  inputProps={{ min: 1, max: 1000 }}
                  sx={{ width: 150 }}
                />
              </Box>

              <Divider sx={{ mb: 2 }} />

              <Typography variant="subtitle2" gutterBottom>
                Steps
              </Typography>
              {cycle.steps.map((step, stepIndex) => (
                <Box key={stepIndex}>
                  {renderStepEditor(step, cycleIndex, stepIndex)}
                </Box>
              ))}

              <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                  Quick Add Step:
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 1 }}>
                  {QUICK_STEPS.map((preset, i) => (
                    <Chip
                      key={i}
                      label={preset.label}
                      size="small"
                      onClick={() => {
                        updateCycle(cycleIndex, {
                          steps: [...definition.cycles[cycleIndex].steps, { ...preset.step }],
                        })
                      }}
                      clickable
                      variant="outlined"
                      color="primary"
                    />
                  ))}
                </Box>
                <Button
                  startIcon={<AddIcon />}
                  size="small"
                  variant="outlined"
                  onClick={() => addStep(cycleIndex)}
                >
                  Add Custom Step
                </Button>
              </Box>
            </AccordionDetails>
          </Accordion>
        ))}
      </Box>

      {/* Preview Section */}
      <Paper sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="subtitle2">
            Preview Generated Steps
          </Typography>
          <Button
            startIcon={<PreviewIcon />}
            size="small"
            variant="outlined"
            onClick={handlePreview}
            disabled={previewLoading}
          >
            {previewLoading ? 'Loading...' : 'Preview'}
          </Button>
        </Box>

        {previewResult && (
          <>
            {!previewResult.valid && previewResult.errors.length > 0 && (
              <Alert severity="error" sx={{ mb: 2 }}>
                <Typography variant="subtitle2">Validation Errors:</Typography>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {previewResult.errors.map((error, i) => (
                    <li key={i}>{error}</li>
                  ))}
                </ul>
              </Alert>
            )}

            {previewResult.valid && previewResult.preview && (
              <Alert severity="success" sx={{ mb: 2 }}>
                <Typography variant="subtitle2">
                  Valid experiment with {previewResult.total_cycles} cycle group(s)
                </Typography>
              </Alert>
            )}

            {previewResult.preview && (
              <Box sx={{ maxHeight: 300, overflow: 'auto', bgcolor: 'grey.100', p: 1, borderRadius: 1 }}>
                {previewResult.preview.map((cyclePreview, i) => (
                  <Box key={i} sx={{ mb: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      Cycle Group {cyclePreview.cycle}:
                    </Typography>
                    {cyclePreview.steps.map((step, j) => (
                      <Typography
                        key={j}
                        variant="body2"
                        sx={{ fontFamily: 'monospace', pl: 2, fontSize: '0.8rem' }}
                      >
                        {step}
                      </Typography>
                    ))}
                  </Box>
                ))}
              </Box>
            )}
          </>
        )}
      </Paper>
    </Box>
  )
}

export default ExperimentBuilder
