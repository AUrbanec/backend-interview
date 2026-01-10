import { useEffect, useState } from 'react'
import {
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Grid,
  Switch,
  FormControlLabel,
  Alert,
  Button,
  Tooltip,
  CircularProgress,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  Lightbulb as LightbulbIcon,
} from '@mui/icons-material'
import { pybammApi, PyBAMMModelOption } from '../services/api'

export type ModelType = 'SPM' | 'SPMe' | 'DFN' | 'MPM' | 'NewmanTobias'

export interface ModelOptions {
  thermal?: string
  SEI?: string
  'SEI porosity change'?: string
  'SEI on cracks'?: string
  'lithium plating'?: string
  'lithium plating porosity change'?: string
  particle?: string
  'particle size'?: string
  'particle mechanics'?: string
  'loss of active material'?: string
  'intercalation kinetics'?: string
  [key: string]: string | undefined
}

interface AdvancedModelOptionsProps {
  modelType: ModelType
  modelOptions: ModelOptions
  onModelTypeChange: (modelType: ModelType) => void
  onModelOptionsChange: (options: ModelOptions) => void
  expanded?: boolean
}

const modelTypeDescriptions: Record<ModelType, string> = {
  SPM: 'Single Particle Model - Fast, good for quick screening',
  SPMe: 'SPM with Electrolyte - Balanced speed/accuracy',
  DFN: 'Doyle-Fuller-Newman - Full physics, most accurate',
  MPM: 'Many Particle Model - For particle size distributions',
  NewmanTobias: 'Simplified DFN - Fast with reasonable accuracy',
}

const AdvancedModelOptions = ({
  modelType,
  modelOptions,
  onModelTypeChange,
  onModelOptionsChange,
  expanded = false,
}: AdvancedModelOptionsProps) => {
  const [isExpanded, setIsExpanded] = useState(expanded)
  const [availableOptions, setAvailableOptions] = useState<Record<string, PyBAMMModelOption> | null>(null)
  const [loading, setLoading] = useState(true)
  const [recommendations, setRecommendations] = useState<{
    model: string
    options: Record<string, string>
    description: string
  } | null>(null)

  useEffect(() => {
    loadOptions()
  }, [])

  const loadOptions = async () => {
    try {
      const optionsData = await pybammApi.getModelOptions()
      setAvailableOptions(optionsData)
    } catch (err) {
      console.error('Failed to load model options:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadRecommendation = async (useCase: string) => {
    try {
      const rec = await pybammApi.getRecommendations(useCase)
      setRecommendations(rec)
      // Apply recommendation
      onModelTypeChange(rec.model as ModelType)
      onModelOptionsChange(rec.options as ModelOptions)
    } catch (err) {
      console.error('Failed to load recommendation:', err)
    }
  }

  const handleOptionChange = (key: string, value: string) => {
    onModelOptionsChange({
      ...modelOptions,
      [key]: value,
    })
  }

  const handleToggleOption = (key: string, enabledValue: string, disabledValue: string) => {
    const currentValue = modelOptions[key]
    const newValue = currentValue === enabledValue ? disabledValue : enabledValue
    handleOptionChange(key, newValue)
  }

  // Key options to show prominently
  const keyOptions = [
    'thermal',
    'SEI',
    'lithium plating',
    'particle',
    'particle mechanics',
    'loss of active material',
  ]

  // Boolean-like options
  const booleanOptions = [
    'SEI porosity change',
    'SEI on cracks',
    'lithium plating porosity change',
  ]

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
        <CircularProgress size={24} />
      </Box>
    )
  }

  return (
    <Accordion expanded={isExpanded} onChange={() => setIsExpanded(!isExpanded)}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
          <Typography variant="subtitle1">Advanced Model Options</Typography>
          <Chip label={modelType} size="small" color="primary" />
          {Object.keys(modelOptions).length > 0 && (
            <Chip 
              label={`${Object.keys(modelOptions).length} custom options`} 
              size="small" 
              variant="outlined" 
            />
          )}
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        {/* Quick Recommendations */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <LightbulbIcon fontSize="small" /> Quick Presets
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Button size="small" variant="outlined" onClick={() => loadRecommendation('fast')}>
              Fast Screening
            </Button>
            <Button size="small" variant="outlined" onClick={() => loadRecommendation('accurate')}>
              Accurate
            </Button>
            <Button size="small" variant="outlined" onClick={() => loadRecommendation('thermal')}>
              Thermal Analysis
            </Button>
            <Button size="small" variant="outlined" onClick={() => loadRecommendation('degradation')}>
              Degradation
            </Button>
            <Button size="small" variant="outlined" onClick={() => loadRecommendation('optimization')}>
              Optimization
            </Button>
          </Box>
          {recommendations && (
            <Alert severity="info" sx={{ mt: 1 }}>
              {recommendations.description}
            </Alert>
          )}
        </Box>

        {/* Model Type Selection */}
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Model Type</InputLabel>
              <Select
                value={modelType}
                label="Model Type"
                onChange={(e) => onModelTypeChange(e.target.value as ModelType)}
              >
                {Object.entries(modelTypeDescriptions).map(([key, desc]) => (
                  <MenuItem key={key} value={key}>
                    <Box>
                      <Typography variant="body1">{key}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {desc}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          {/* Key Options */}
          {availableOptions && keyOptions.map((optionKey) => {
            const option = availableOptions[optionKey]
            if (!option) return null
            
            return (
              <Grid item xs={12} md={6} key={optionKey}>
                <FormControl fullWidth>
                  <InputLabel>{optionKey}</InputLabel>
                  <Select
                    value={modelOptions[optionKey] || option.default}
                    label={optionKey}
                    onChange={(e) => handleOptionChange(optionKey, e.target.value)}
                  >
                    {option.options.map((opt) => (
                      <MenuItem key={String(opt)} value={String(opt)}>
                        {String(opt)}
                        {option.details?.[String(opt)] && (
                          <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                            - {option.details[String(opt)]}
                          </Typography>
                        )}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            )
          })}

          {/* Boolean Toggle Options */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
              Additional Options
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              {availableOptions && booleanOptions.map((optionKey) => {
                const option = availableOptions[optionKey]
                if (!option) return null
                
                const isEnabled = modelOptions[optionKey] === 'true'
                
                return (
                  <Tooltip key={optionKey} title={option.description}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={isEnabled}
                          onChange={() => handleToggleOption(optionKey, 'true', 'false')}
                          size="small"
                        />
                      }
                      label={optionKey}
                    />
                  </Tooltip>
                )
              })}
            </Box>
          </Grid>
        </Grid>

        {/* Current Configuration Summary */}
        {Object.keys(modelOptions).length > 0 && (
          <Box sx={{ mt: 2, p: 1, bgcolor: 'grey.100', borderRadius: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Current Configuration:
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
              {Object.entries(modelOptions).map(([key, value]) => (
                value && (
                  <Chip
                    key={key}
                    label={`${key}: ${value}`}
                    size="small"
                    onDelete={() => {
                      const newOptions = { ...modelOptions }
                      delete newOptions[key]
                      onModelOptionsChange(newOptions)
                    }}
                  />
                )
              ))}
            </Box>
          </Box>
        )}
      </AccordionDetails>
    </Accordion>
  )
}

export default AdvancedModelOptions
