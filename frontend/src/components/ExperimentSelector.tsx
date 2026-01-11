import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  CardActionArea,
  Typography,
  Grid,
  Chip,
  Slider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Collapse,
  Button,
  Alert,
} from '@mui/material'
import {
  FlashOn as QuickIcon,
  Loop as CycleIcon,
  Speed as RateIcon,
  Thermostat as ThermalIcon,
  Timeline as CustomIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material'
import ExperimentBuilder from './ExperimentBuilder'
import { ExperimentDefinition, ExperimentTemplateResponse } from '../services/api'

export type ProtocolType = 'standard_cycle' | 'capacity_check' | 'rate_capability' | 'drive_cycle' | 'hppc' | 'custom'
export type ExperimentMode = 'protocol' | 'custom' | 'template'

// Default experiment definition for custom mode
const DEFAULT_EXPERIMENT_DEFINITION: ExperimentDefinition = {
  cycles: [
    {
      steps: [
        {
          step_type: 'string',
          step_string: 'Discharge at 1C until 3.0V',
        },
      ],
      repeat: 1,
    },
  ],
  default_period: '1 minute',
  default_temperature_celsius: 25.0,
}

interface QuickExperiment {
  id: string
  name: string
  description: string
  icon: React.ReactNode
  protocol: ProtocolType
  defaultCRate: number
  defaultCycles: number
}

const QUICK_EXPERIMENTS: QuickExperiment[] = [
  {
    id: 'discharge',
    name: 'Quick Discharge',
    description: 'Single CC discharge at selected C-rate',
    icon: <QuickIcon />,
    protocol: 'standard_cycle',
    defaultCRate: 1.0,
    defaultCycles: 1,
  },
  {
    id: 'cccv_cycle',
    name: 'CCCV Cycle',
    description: 'Standard charge/discharge cycle',
    icon: <CycleIcon />,
    protocol: 'standard_cycle',
    defaultCRate: 1.0,
    defaultCycles: 1,
  },
  {
    id: 'capacity_check',
    name: 'Capacity Check',
    description: 'C/20 discharge for baseline capacity',
    icon: <ThermalIcon />,
    protocol: 'capacity_check',
    defaultCRate: 0.05,
    defaultCycles: 1,
  },
  {
    id: 'rate_test',
    name: 'Rate Capability',
    description: 'Multi C-rate test (C/5 to 3C)',
    icon: <RateIcon />,
    protocol: 'rate_capability',
    defaultCRate: 1.0,
    defaultCycles: 5,
  },
  {
    id: 'hppc',
    name: 'HPPC Test',
    description: 'Hybrid Pulse Power Characterization',
    icon: <QuickIcon />,
    protocol: 'hppc',
    defaultCRate: 1.0,
    defaultCycles: 1,
  },
  {
    id: 'custom',
    name: 'Custom Experiment',
    description: 'Build your own experiment steps',
    icon: <CustomIcon />,
    protocol: 'custom',
    defaultCRate: 1.0,
    defaultCycles: 1,
  },
]

interface ExperimentSelectorProps {
  protocol: ProtocolType
  cRate: number
  temperatureCelsius: number
  cycles: number
  experimentMode: ExperimentMode
  experimentDefinition: ExperimentDefinition | null
  experimentTemplateId: string
  templates: ExperimentTemplateResponse[]
  onProtocolChange: (protocol: ProtocolType) => void
  onCRateChange: (cRate: number) => void
  onTemperatureChange: (temp: number) => void
  onCyclesChange: (cycles: number) => void
  onExperimentModeChange: (mode: ExperimentMode) => void
  onExperimentDefinitionChange: (def: ExperimentDefinition | null) => void
  onTemplateIdChange: (id: string) => void
}

const ExperimentSelector = ({
  protocol,
  cRate,
  temperatureCelsius,
  cycles,
  experimentMode,
  experimentDefinition,
  experimentTemplateId,
  templates,
  onProtocolChange,
  onCRateChange,
  onTemperatureChange,
  onCyclesChange,
  onExperimentModeChange,
  onExperimentDefinitionChange,
  onTemplateIdChange,
}: ExperimentSelectorProps) => {
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [selectedQuick, setSelectedQuick] = useState<string | null>(
    protocol === 'custom' ? 'custom' : QUICK_EXPERIMENTS.find(e => e.protocol === protocol)?.id || null
  )

  const handleQuickSelect = (experiment: QuickExperiment) => {
    setSelectedQuick(experiment.id)
    onProtocolChange(experiment.protocol)
    onCRateChange(experiment.defaultCRate)
    onCyclesChange(experiment.defaultCycles)
    
    if (experiment.protocol === 'custom') {
      onExperimentModeChange('custom')
      // Initialize with default experiment definition if not already set
      if (!experimentDefinition) {
        onExperimentDefinitionChange(DEFAULT_EXPERIMENT_DEFINITION)
      }
    } else {
      onExperimentModeChange('protocol')
    }
  }

  const isCustomMode = experimentMode === 'custom' || protocol === 'custom'

  return (
    <Box>
      {/* Quick Experiment Selection */}
      <Typography variant="subtitle2" gutterBottom>
        Select Experiment Type
      </Typography>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {QUICK_EXPERIMENTS.map((experiment) => (
          <Grid item xs={6} sm={4} md={2} key={experiment.id}>
            <Card
              variant={selectedQuick === experiment.id ? 'elevation' : 'outlined'}
              sx={{
                border: selectedQuick === experiment.id ? '2px solid' : undefined,
                borderColor: selectedQuick === experiment.id ? 'primary.main' : undefined,
                height: '100%',
              }}
            >
              <CardActionArea
                onClick={() => handleQuickSelect(experiment)}
                sx={{ height: '100%', p: 1 }}
              >
                <CardContent sx={{ textAlign: 'center', p: 1 }}>
                  <Box sx={{ color: selectedQuick === experiment.id ? 'primary.main' : 'text.secondary', mb: 1 }}>
                    {experiment.icon}
                  </Box>
                  <Typography variant="body2" fontWeight="bold">
                    {experiment.name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block">
                    {experiment.description}
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Operating Conditions (for non-custom experiments) */}
      {!isCustomMode && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Operating Conditions
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Typography gutterBottom>
                C-Rate: <strong>{cRate < 1 ? `C/${Math.round(1/cRate)}` : `${cRate}C`}</strong>
              </Typography>
              <Slider
                value={cRate}
                onChange={(_, v) => onCRateChange(v as number)}
                min={0.05}
                max={5}
                step={0.05}
                marks={[
                  { value: 0.05, label: 'C/20' },
                  { value: 0.5, label: 'C/2' },
                  { value: 1, label: '1C' },
                  { value: 2, label: '2C' },
                  { value: 5, label: '5C' },
                ]}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <Typography gutterBottom>
                Temperature: <strong>{temperatureCelsius}°C</strong>
              </Typography>
              <Slider
                value={temperatureCelsius}
                onChange={(_, v) => onTemperatureChange(v as number)}
                min={-20}
                max={60}
                step={5}
                marks={[
                  { value: -20, label: '-20°C' },
                  { value: 0, label: '0°C' },
                  { value: 25, label: '25°C' },
                  { value: 45, label: '45°C' },
                  { value: 60, label: '60°C' },
                ]}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <Typography gutterBottom>
                Cycles: <strong>{cycles}</strong>
                {cycles > 50 && <Chip label="Long sim" size="small" color="warning" sx={{ ml: 1 }} />}
              </Typography>
              <Slider
                value={cycles}
                onChange={(_, v) => onCyclesChange(v as number)}
                min={1}
                max={100}
                step={1}
                marks={[
                  { value: 1, label: '1' },
                  { value: 25, label: '25' },
                  { value: 50, label: '50' },
                  { value: 100, label: '100' },
                ]}
              />
            </Grid>
          </Grid>
        </Box>
      )}

      {/* Template Selection (alternative to custom) */}
      {!isCustomMode && templates.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Button
            size="small"
            onClick={() => setShowAdvanced(!showAdvanced)}
            endIcon={showAdvanced ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          >
            {showAdvanced ? 'Hide' : 'Show'} Template Options
          </Button>
          <Collapse in={showAdvanced}>
            <Box sx={{ mt: 2 }}>
              <FormControl fullWidth size="small">
                <InputLabel>Use Saved Template Instead</InputLabel>
                <Select
                  value={experimentTemplateId}
                  label="Use Saved Template Instead"
                  onChange={(e) => {
                    onTemplateIdChange(e.target.value)
                    if (e.target.value) {
                      onExperimentModeChange('template')
                    } else {
                      onExperimentModeChange('protocol')
                    }
                  }}
                >
                  <MenuItem value="">
                    <em>None - Use selected protocol</em>
                  </MenuItem>
                  {templates.map((template) => (
                    <MenuItem key={template.id} value={template.id}>
                      {template.name}
                      {template.description && (
                        <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                          - {template.description}
                        </Typography>
                      )}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
          </Collapse>
        </Box>
      )}

      {/* Custom Experiment Builder */}
      {isCustomMode && (
        <Box>
          <Alert severity="info" sx={{ mb: 2 }}>
            Build a custom experiment using PyBaMM experiment steps. You can define charge/discharge steps,
            rest periods, and more with precise control over termination conditions.
          </Alert>
          <ExperimentBuilder
            value={experimentDefinition}
            onChange={(def) => onExperimentDefinitionChange(def)}
            templates={templates}
          />
        </Box>
      )}

      {/* Summary */}
      {!isCustomMode && (
        <Alert severity="success" sx={{ mt: 2 }}>
          <Typography variant="body2">
            <strong>Experiment:</strong> {QUICK_EXPERIMENTS.find(e => e.id === selectedQuick)?.name || protocol}
            {' • '}
            <strong>C-Rate:</strong> {cRate < 1 ? `C/${Math.round(1/cRate)}` : `${cRate}C`}
            {' • '}
            <strong>Temp:</strong> {temperatureCelsius}°C
            {' • '}
            <strong>Cycles:</strong> {cycles}
          </Typography>
        </Alert>
      )}
    </Box>
  )
}

export default ExperimentSelector
