import { useEffect, useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  Card,
  CardContent,
  Chip,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Alert,
  Tooltip,
  IconButton,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  Speed as SpeedIcon,
  Memory as MemoryIcon,
  Thermostat as ThermostatIcon,
  Science as ScienceIcon,
  Info as InfoIcon,
} from '@mui/icons-material'
import { pybammApi, PyBAMMModel, PyBAMMModelOption, PyBAMMParameterSet } from '../services/api'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ py: 2 }}>{children}</Box>}
    </div>
  )
}

const complexityColors: Record<string, 'success' | 'warning' | 'error' | 'info'> = {
  'very low': 'success',
  'low': 'success',
  'medium-low': 'info',
  'medium': 'warning',
  'high': 'error',
  'very high': 'error',
}

const PyBAMMReference = () => {
  const [tabValue, setTabValue] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  const [models, setModels] = useState<{
    lithium_ion: Record<string, PyBAMMModel>
    lead_acid: Record<string, PyBAMMModel>
    equivalent_circuit: Record<string, PyBAMMModel>
  } | null>(null)
  
  const [modelOptions, setModelOptions] = useState<Record<string, PyBAMMModelOption> | null>(null)
  const [parameterSets, setParameterSets] = useState<Record<string, PyBAMMParameterSet> | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [modelsData, optionsData, setsData] = await Promise.all([
        pybammApi.getModels(),
        pybammApi.getModelOptions(),
        pybammApi.getParameterSets(),
      ])
      setModels(modelsData)
      setModelOptions(optionsData)
      setParameterSets(setsData)
    } catch (err) {
      setError('Failed to load PyBAMM reference data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <ScienceIcon /> PyBAMM Reference
      </Typography>
      
      <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tab label="Models" icon={<MemoryIcon />} iconPosition="start" />
        <Tab label="Model Options" icon={<ThermostatIcon />} iconPosition="start" />
        <Tab label="Parameter Sets" icon={<SpeedIcon />} iconPosition="start" />
      </Tabs>

      {/* Models Tab */}
      <TabPanel value={tabValue} index={0}>
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          Available battery models in PyBAMM. Higher complexity = more accurate but slower.
        </Typography>
        
        <Typography variant="overline" sx={{ mt: 2, display: 'block' }}>Lithium-Ion Models</Typography>
        <Grid container spacing={2}>
          {models && Object.entries(models.lithium_ion).map(([key, model]) => (
            <Grid item xs={12} md={6} lg={4} key={key}>
              <Card variant="outlined">
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Typography variant="h6">{key}</Typography>
                    <Chip 
                      label={model.complexity} 
                      size="small" 
                      color={complexityColors[model.complexity] || 'default'}
                    />
                  </Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {model.name}
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    {model.description}
                  </Typography>
                  <Typography variant="caption" color="primary">
                    <strong>Best for:</strong> {model.recommended_use}
                  </Typography>
                  {model.variants && model.variants.length > 1 && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Variants: {model.variants.join(', ')}
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        {models && Object.keys(models.lead_acid).length > 0 && (
          <>
            <Typography variant="overline" sx={{ mt: 3, display: 'block' }}>Lead-Acid Models</Typography>
            <Grid container spacing={2}>
              {Object.entries(models.lead_acid).map(([key, model]) => (
                <Grid item xs={12} md={6} lg={4} key={key}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6">{key}</Typography>
                      <Typography variant="body2">{model.description}</Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </>
        )}

        {models && Object.keys(models.equivalent_circuit).length > 0 && (
          <>
            <Typography variant="overline" sx={{ mt: 3, display: 'block' }}>Equivalent Circuit Models</Typography>
            <Grid container spacing={2}>
              {Object.entries(models.equivalent_circuit).map(([key, model]) => (
                <Grid item xs={12} md={6} lg={4} key={key}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="h6">{key}</Typography>
                      <Typography variant="body2">{model.description}</Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </>
        )}
      </TabPanel>

      {/* Model Options Tab */}
      <TabPanel value={tabValue} index={1}>
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          Advanced model options (submodels) available in PyBAMM. These control physics like thermal effects, degradation, etc.
        </Typography>
        
        {modelOptions && Object.entries(modelOptions).map(([key, option]) => (
          <Accordion key={key} sx={{ mt: 1 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                <Typography sx={{ fontWeight: 'medium', minWidth: 200 }}>{key}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ flexGrow: 1 }}>
                  {option.description}
                </Typography>
                <Chip label={`Default: ${option.default}`} size="small" variant="outlined" />
                {option.electrode_specific && (
                  <Tooltip title="Can be set differently for negative and positive electrodes">
                    <Chip label="Electrode-specific" size="small" color="info" />
                  </Tooltip>
                )}
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                {option.options.map((opt) => (
                  <Chip 
                    key={String(opt)} 
                    label={String(opt)} 
                    variant={String(opt) === option.default ? 'filled' : 'outlined'}
                    color={String(opt) === option.default ? 'primary' : 'default'}
                    size="small"
                  />
                ))}
              </Box>
              {option.details && (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Option</TableCell>
                        <TableCell>Description</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {Object.entries(option.details).map(([optKey, desc]) => (
                        <TableRow key={optKey}>
                          <TableCell><code>{optKey}</code></TableCell>
                          <TableCell>{desc}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </AccordionDetails>
          </Accordion>
        ))}
      </TabPanel>

      {/* Parameter Sets Tab */}
      <TabPanel value={tabValue} index={2}>
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          Validated parameter sets from published research. Each set contains all parameters needed for a specific cell.
        </Typography>
        
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Chemistry</TableCell>
                <TableCell>Cell Type</TableCell>
                <TableCell>Format</TableCell>
                <TableCell>Reference</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {parameterSets && Object.entries(parameterSets).map(([name, set]) => (
                <TableRow key={name} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">{name}</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={set.chemistry} size="small" />
                  </TableCell>
                  <TableCell>{set.cell_type}</TableCell>
                  <TableCell>{set.cell_format || '-'}</TableCell>
                  <TableCell>
                    <Tooltip title={set.reference}>
                      <IconButton size="small">
                        <InfoIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </TabPanel>
    </Paper>
  )
}

export default PyBAMMReference
