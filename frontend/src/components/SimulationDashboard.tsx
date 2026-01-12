import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import {
  Container,
  Paper,
  Typography,
  Button,
  Box,
  Grid,
  Card,
  CardContent,
  CardActions,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Slider,
  CircularProgress,
  LinearProgress,
  AppBar,
  Toolbar,
  Alert,
  Tabs,
  Tab,
} from '@mui/material'
import {
  Add as AddIcon,
  Logout as LogoutIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Cancel as CancelIcon,
  Science as ScienceIcon,
  Assessment as AssessmentIcon,
  CompareArrows as CompareArrowsIcon,
} from '@mui/icons-material'
import { signOut } from '../redux/slices/authSlice'
import {
  fetchSimulations,
  createSimulation,
  deleteSimulation,
  cancelSimulation,
  fetchSimulation,
  Simulation,
  SimulationStatus,
  BatteryChemistry,
  ProtocolType,
  ThermalMode,
  ModelType,
  CreateSimulationParams,
} from '../redux/slices/simulationsSlice'
import { fetchPresets, Preset } from '../redux/slices/presetsSlice'
import { fetchTodos, createTodo, updateTodo, deleteTodo, Todo } from '../redux/slices/todosSlice'
import { AppDispatch, RootState } from '../redux/store/store'
import { useAuthContext } from '../auth/hooks'
import { usageApi } from '../services/api'
import SimulationChart from './SimulationChart'
import PyBAMMReference from './PyBAMMReference'
import AdvancedModelOptions, { ModelOptions } from './AdvancedModelOptions'
import {
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Checkbox,
  Link as MuiLink,
} from '@mui/material'
import { Assignment as AssignmentIcon } from '@mui/icons-material'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  )
}

const statusColors: Record<SimulationStatus, 'default' | 'primary' | 'success' | 'error' | 'warning'> = {
  pending: 'default',
  running: 'primary',
  completed: 'success',
  failed: 'error',
  cancelled: 'warning',
}

const chemistryOptions: BatteryChemistry[] = ['LFP', 'NMC', 'NCA', 'LCO', 'custom']

const SimulationDashboard = () => {
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const { user } = useAuthContext()
  const { simulations, loading } = useSelector((state: RootState) => state.simulations)
  const { presets } = useSelector((state: RootState) => state.presets)
  const { todos, loading: todosLoading } = useSelector((state: RootState) => state.todos)
  
  const [tabValue, setTabValue] = useState(0)
  const [openDialog, setOpenDialog] = useState(false)
  const [openTodoDialog, setOpenTodoDialog] = useState(false)
  const [selectedSimulations, setSelectedSimulations] = useState<Simulation[]>([])
  const [usageData, setUsageData] = useState<{
    simulations_count: number
    simulations_limit: number
    usage_percentage: number
  } | null>(null)
  
  // New simulation form state
  const [newSim, setNewSim] = useState<CreateSimulationParams>({
    name: '',
    description: '',
    chemistry: 'LFP',
    protocol: 'standard_cycle',
    c_rate: 1.0,
    temperature_celsius: 25.0,
    cycles: 1,
  })
  
  // Thermal settings state
  const [thermalMode, setThermalMode] = useState<ThermalMode>('isothermal')
  const [heatTransferCoeff, setHeatTransferCoeff] = useState<number>(10)
  const [externalCoolingTemp, setExternalCoolingTemp] = useState<number>(25)
  
  // Advanced model options state
  const [modelType, setModelType] = useState<ModelType>('DFN')
  const [modelOptions, setModelOptions] = useState<ModelOptions>({})

  // New todo form state
  const [newTodo, setNewTodo] = useState({
    title: '',
    description: '',
    simulation_id: '',
  })

  useEffect(() => {
    dispatch(fetchSimulations())
    dispatch(fetchPresets())
    dispatch(fetchTodos())
    loadUsage()
  }, [dispatch])

  // Poll for running simulations
  useEffect(() => {
    const runningSimulations = simulations.filter(s => s.status === 'running' || s.status === 'pending')
    if (runningSimulations.length === 0) return

    const interval = setInterval(() => {
      runningSimulations.forEach(sim => {
        dispatch(fetchSimulation(sim.id))
      })
    }, 3000)

    return () => clearInterval(interval)
  }, [simulations, dispatch])

  const loadUsage = async () => {
    try {
      const data = await usageApi.getUsage()
      setUsageData(data)
    } catch (error) {
      console.error('Failed to load usage:', error)
    }
  }

  const handleSignOut = async () => {
    await dispatch(signOut())
    navigate('/login')
  }

  const handleCreateSimulation = async () => {
    if (newSim.name.trim()) {
      // Build custom_parameters with thermal settings
      const customParams: Record<string, unknown> = { ...newSim.custom_parameters }
      
      if (thermalMode === 'lumped') {
        customParams.thermal_mode = 'lumped'
        customParams.heat_transfer_coefficient = heatTransferCoeff
        customParams.external_cooling_temperature_celsius = externalCoolingTemp
      } else {
        customParams.thermal_mode = 'isothermal'
      }
      
      // Add model options to custom_parameters
      Object.entries(modelOptions).forEach(([key, value]) => {
        if (value) {
          customParams[key] = value
        }
      })
      
      // Filter out undefined values from model options
      const filteredModelOptions: Record<string, string> = {}
      Object.entries(modelOptions).forEach(([key, value]) => {
        if (value !== undefined) {
          filteredModelOptions[key] = value
        }
      })
      
      await dispatch(createSimulation({
        ...newSim,
        model_type: modelType,
        model_options: filteredModelOptions,
        custom_parameters: customParams,
      }))
      
      // Reset form
      setNewSim({
        name: '',
        description: '',
        chemistry: 'LFP',
        protocol: 'standard_cycle',
        c_rate: 1.0,
        temperature_celsius: 25.0,
        cycles: 1,
      })
      setThermalMode('isothermal')
      setHeatTransferCoeff(10)
      setExternalCoolingTemp(25)
      setModelType('DFN')
      setModelOptions({})
      setOpenDialog(false)
      loadUsage()
    }
  }

  const handleDeleteSimulation = async (id: string) => {
    await dispatch(deleteSimulation(id))
  }

  const handleCancelSimulation = async (id: string) => {
    await dispatch(cancelSimulation(id))
  }

  const handleApplyPreset = (preset: Preset) => {
    setNewSim({
      ...newSim,
      chemistry: preset.chemistry,
      c_rate: preset.c_rate,
      temperature_celsius: preset.temperature_celsius,
      cycles: preset.cycles,
    })
  }

  const handleViewResults = (simulation: Simulation) => {
    setSelectedSimulations([simulation])
    setTabValue(1)
  }

  const handleToggleSimulationSelection = (simulation: Simulation) => {
    setSelectedSimulations(prev => {
      const isSelected = prev.some(s => s.id === simulation.id)
      if (isSelected) {
        return prev.filter(s => s.id !== simulation.id)
      } else {
        return [...prev, simulation]
      }
    })
  }

  const handleCompareSelected = () => {
    if (selectedSimulations.length >= 1) {
      setTabValue(1)
    }
  }

  const handleClearSelection = () => {
    setSelectedSimulations([])
  }

  const isSimulationSelected = (id: string) => selectedSimulations.some(s => s.id === id)

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString()
  }

  // Todo handlers
  const handleCreateTodo = async () => {
    if (newTodo.title.trim()) {
      await dispatch(createTodo({
        title: newTodo.title,
        description: newTodo.description || undefined,
        simulation_id: newTodo.simulation_id || undefined,
      }))
      setNewTodo({ title: '', description: '', simulation_id: '' })
      setOpenTodoDialog(false)
    }
  }

  const handleToggleTodo = async (todo: Todo) => {
    await dispatch(updateTodo({ id: todo.id, completed: !todo.completed }))
  }

  const handleDeleteTodo = async (id: string) => {
    await dispatch(deleteTodo(id))
  }

  const getSimulationName = (simId: string | null | undefined) => {
    if (!simId) return null
    const sim = simulations.find(s => s.id === simId)
    return sim?.name || 'Unknown Simulation'
  }

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <ScienceIcon sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Battery Simulation Platform
          </Typography>
          <Typography variant="body2" sx={{ mr: 2 }}>
            {user?.email}
          </Typography>
          <IconButton color="inherit" onClick={handleSignOut}>
            <LogoutIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 4 }}>
        {/* Usage Stats Banner */}
        {usageData && (
          <Paper sx={{ p: 2, mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="body1">
                Monthly Usage: {usageData.simulations_count} / {usageData.simulations_limit} simulations
              </Typography>
              <Box sx={{ width: 200 }}>
                <LinearProgress 
                  variant="determinate" 
                  value={usageData.usage_percentage} 
                  color={usageData.usage_percentage > 80 ? 'error' : 'primary'}
                />
              </Box>
            </Box>
          </Paper>
        )}

        <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} sx={{ mb: 2 }}>
          <Tab label="Simulations" icon={<ScienceIcon />} iconPosition="start" />
          <Tab label="Results Viewer" icon={<AssessmentIcon />} iconPosition="start" />
          <Tab label="Tasks" icon={<AssignmentIcon />} iconPosition="start" />
          <Tab label="PyBAMM Reference" icon={<ScienceIcon />} iconPosition="start" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
            <Typography variant="h5">My Simulations</Typography>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              {selectedSimulations.length > 0 && (
                <>
                  <Chip 
                    label={`${selectedSimulations.length} selected`} 
                    onDelete={handleClearSelection}
                    color="primary"
                    size="small"
                  />
                  <Button
                    variant="contained"
                    color="secondary"
                    startIcon={<CompareArrowsIcon />}
                    onClick={handleCompareSelected}
                    disabled={!selectedSimulations.some(s => s.results)}
                  >
                    Compare
                  </Button>
                </>
              )}
              <Button
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={() => dispatch(fetchSimulations())}
              >
                Refresh
              </Button>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => setOpenDialog(true)}
              >
                New Simulation
              </Button>
            </Box>
          </Box>

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Grid container spacing={3}>
              {simulations.length === 0 ? (
                <Grid item xs={12}>
                  <Alert severity="info">
                    No simulations yet. Create your first battery simulation!
                  </Alert>
                </Grid>
              ) : (
                simulations.map((sim) => (
                  <Grid item xs={12} md={6} lg={4} key={sim.id}>
                    <Card 
                      sx={{ 
                        border: isSimulationSelected(sim.id) ? '2px solid' : 'none',
                        borderColor: 'primary.main',
                      }}
                    >
                      <CardContent>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, maxWidth: '70%' }}>
                            {sim.status === 'completed' && sim.results && (
                              <Checkbox
                                checked={isSimulationSelected(sim.id)}
                                onChange={() => handleToggleSimulationSelection(sim)}
                                size="small"
                                sx={{ p: 0 }}
                              />
                            )}
                            <Typography variant="h6" noWrap>
                              {sim.name}
                            </Typography>
                          </Box>
                          <Chip
                            label={sim.status}
                            color={statusColors[sim.status]}
                            size="small"
                          />
                        </Box>
                        
                        {(sim.status === 'running' || sim.status === 'pending') && (
                          <LinearProgress 
                            variant="determinate" 
                            value={sim.progress} 
                            sx={{ mb: 1 }}
                          />
                        )}

                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          {sim.description || 'No description'}
                        </Typography>

                        <Box sx={{ mt: 2 }}>
                          <Typography variant="caption" display="block">
                            <strong>Chemistry:</strong> {sim.chemistry}
                          </Typography>
                          <Typography variant="caption" display="block">
                            <strong>C-Rate:</strong> {sim.c_rate}C
                          </Typography>
                          <Typography variant="caption" display="block">
                            <strong>Temperature:</strong> {sim.temperature_celsius}°C
                          </Typography>
                          <Typography variant="caption" display="block">
                            <strong>Cycles:</strong> {sim.cycles}
                          </Typography>
                          <Typography variant="caption" display="block" color="text.secondary">
                            Created: {formatDate(sim.created_at)}
                          </Typography>
                        </Box>

                        {sim.error_message && (
                          <Alert severity="error" sx={{ mt: 1 }}>
                            {sim.error_message}
                          </Alert>
                        )}
                      </CardContent>
                      <CardActions>
                        {sim.status === 'completed' && sim.results && (
                          <Button size="small" onClick={() => handleViewResults(sim)}>
                            View Results
                          </Button>
                        )}
                        {(sim.status === 'running' || sim.status === 'pending') && (
                          <IconButton 
                            size="small" 
                            color="warning"
                            onClick={() => handleCancelSimulation(sim.id)}
                          >
                            <CancelIcon />
                          </IconButton>
                        )}
                        <IconButton 
                          size="small" 
                          color="error"
                          onClick={() => handleDeleteSimulation(sim.id)}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </CardActions>
                    </Card>
                  </Grid>
                ))
              )}
            </Grid>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          {selectedSimulations.length > 0 && selectedSimulations.some(s => s.results) ? (
            <SimulationChart simulations={selectedSimulations} />
          ) : (
            <Alert severity="info">
              Select one or more completed simulations from the Simulations tab to view and compare results.
            </Alert>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
            <Typography variant="h5">My Tasks</Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setOpenTodoDialog(true)}
            >
              New Task
            </Button>
          </Box>

          {todosLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Paper>
              <List>
                {todos.length === 0 ? (
                  <ListItem>
                    <ListItemText primary="No tasks yet. Create your first task!" />
                  </ListItem>
                ) : (
                  todos.map((todo) => (
                    <ListItem key={todo.id} divider>
                      <Checkbox
                        checked={todo.completed}
                        onChange={() => handleToggleTodo(todo)}
                      />
                      <ListItemText
                        primary={todo.title}
                        secondary={
                          <Box component="span">
                            {todo.description && <span>{todo.description}<br /></span>}
                            {todo.simulation_id && (
                              <MuiLink
                                component="button"
                                variant="caption"
                                onClick={() => {
                                  const sim = simulations.find(s => s.id === todo.simulation_id)
                                  if (sim) {
                                    setSelectedSimulations([sim])
                                    setTabValue(1)
                                  }
                                }}
                                sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
                              >
                                <ScienceIcon fontSize="inherit" />
                                Linked: {getSimulationName(todo.simulation_id)}
                              </MuiLink>
                            )}
                          </Box>
                        }
                        sx={{
                          textDecoration: todo.completed ? 'line-through' : 'none',
                          opacity: todo.completed ? 0.6 : 1,
                        }}
                      />
                      <ListItemSecondaryAction>
                        <IconButton
                          edge="end"
                          aria-label="delete"
                          onClick={() => handleDeleteTodo(todo.id)}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </ListItemSecondaryAction>
                    </ListItem>
                  ))
                )}
              </List>
            </Paper>
          )}
        </TabPanel>

        {/* PyBAMM Reference Tab */}
        <TabPanel value={tabValue} index={3}>
          <PyBAMMReference />
        </TabPanel>
      </Container>

      {/* New Simulation Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Create New Simulation</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                autoFocus
                label="Simulation Name"
                fullWidth
                value={newSim.name}
                onChange={(e) => setNewSim({ ...newSim, name: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Description"
                fullWidth
                multiline
                rows={2}
                value={newSim.description}
                onChange={(e) => setNewSim({ ...newSim, description: e.target.value })}
              />
            </Grid>
            
            {/* Preset Selection */}
            <Grid item xs={12}>
              <Typography variant="subtitle2" gutterBottom>
                Quick Start with Preset:
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {presets.slice(0, 6).map((preset) => (
                  <Chip
                    key={preset.id}
                    label={preset.name}
                    onClick={() => handleApplyPreset(preset)}
                    variant="outlined"
                    clickable
                  />
                ))}
              </Box>
            </Grid>

            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Battery Chemistry</InputLabel>
                <Select
                  value={newSim.chemistry}
                  label="Battery Chemistry"
                  onChange={(e) => setNewSim({ ...newSim, chemistry: e.target.value as BatteryChemistry })}
                >
                  {chemistryOptions.map((chem) => (
                    <MenuItem key={chem} value={chem}>{chem}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Test Protocol</InputLabel>
                <Select
                  value={newSim.protocol || 'standard_cycle'}
                  label="Test Protocol"
                  onChange={(e) => setNewSim({ 
                    ...newSim, 
                    protocol: e.target.value as ProtocolType
                  })}
                >
                  <MenuItem value="standard_cycle">Standard Cycle (CCCV + CC)</MenuItem>
                  <MenuItem value="capacity_check">Capacity Check (C/20 discharge)</MenuItem>
                  <MenuItem value="rate_capability">Rate Capability (multi C-rate)</MenuItem>
                  <MenuItem value="drive_cycle">Drive Cycle (variable current)</MenuItem>
                  <MenuItem value="hppc">HPPC (Pulse Power)</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography gutterBottom>C-Rate: {newSim.c_rate}C</Typography>
              <Slider
                value={newSim.c_rate}
                onChange={(_, v) => setNewSim({ ...newSim, c_rate: v as number })}
                min={0.05}
                max={10}
                step={0.05}
                marks={[
                  { value: 0.05, label: 'C/20' },
                  { value: 1, label: '1C' },
                  { value: 3, label: '3C' },
                  { value: 5, label: '5C' },
                  { value: 10, label: '10C' },
                ]}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography gutterBottom>Temperature: {newSim.temperature_celsius}°C</Typography>
              <Slider
                value={newSim.temperature_celsius}
                onChange={(_, v) => setNewSim({ ...newSim, temperature_celsius: v as number })}
                min={-20}
                max={60}
                step={1}
                marks={[
                  { value: -20, label: '-20°C' },
                  { value: 0, label: '0°C' },
                  { value: 25, label: '25°C' },
                  { value: 45, label: '45°C' },
                ]}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography gutterBottom>Cycles: {newSim.cycles}{newSim.cycles > 50 ? ' (long simulation)' : ''}</Typography>
              <Slider
                value={newSim.cycles}
                onChange={(_, v) => setNewSim({ ...newSim, cycles: v as number })}
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

            {/* Thermal Settings Section */}
            <Grid item xs={12}>
              <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
                Thermal Model Settings
              </Typography>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Thermal Mode</InputLabel>
                <Select
                  value={thermalMode}
                  label="Thermal Mode"
                  onChange={(e) => setThermalMode(e.target.value as ThermalMode)}
                >
                  <MenuItem value="isothermal">Isothermal (constant temp)</MenuItem>
                  <MenuItem value="lumped">Lumped Thermal (dynamic temp)</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            {thermalMode === 'lumped' && (
              <>
                <Grid item xs={12} md={6}>
                  <Typography gutterBottom>
                    Heat Transfer Coefficient: {heatTransferCoeff} W/m²K
                  </Typography>
                  <Slider
                    value={heatTransferCoeff}
                    onChange={(_, v) => setHeatTransferCoeff(v as number)}
                    min={1}
                    max={200}
                    step={1}
                    marks={[
                      { value: 10, label: '10 (natural)' },
                      { value: 50, label: '50 (forced air)' },
                      { value: 100, label: '100' },
                      { value: 200, label: '200 (liquid)' },
                    ]}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography gutterBottom>
                    External Cooling Temp: {externalCoolingTemp}°C
                  </Typography>
                  <Slider
                    value={externalCoolingTemp}
                    onChange={(_, v) => setExternalCoolingTemp(v as number)}
                    min={-10}
                    max={50}
                    step={1}
                    marks={[
                      { value: 0, label: '0°C' },
                      { value: 25, label: '25°C' },
                      { value: 40, label: '40°C' },
                    ]}
                  />
                </Grid>
              </>
            )}

            {/* Advanced Model Options */}
            <Grid item xs={12}>
              <AdvancedModelOptions
                modelType={modelType}
                modelOptions={modelOptions}
                onModelTypeChange={setModelType}
                onModelOptionsChange={setModelOptions}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleCreateSimulation} 
            variant="contained" 
            disabled={!newSim.name.trim()}
          >
            Start Simulation
          </Button>
        </DialogActions>
      </Dialog>

      {/* New Task Dialog */}
      <Dialog open={openTodoDialog} onClose={() => setOpenTodoDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Task</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                autoFocus
                label="Task Title"
                fullWidth
                value={newTodo.title}
                onChange={(e) => setNewTodo({ ...newTodo, title: e.target.value })}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Description"
                fullWidth
                multiline
                rows={2}
                value={newTodo.description}
                onChange={(e) => setNewTodo({ ...newTodo, description: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Link to Simulation (Optional)</InputLabel>
                <Select
                  value={newTodo.simulation_id}
                  label="Link to Simulation (Optional)"
                  onChange={(e) => setNewTodo({ ...newTodo, simulation_id: e.target.value })}
                >
                  <MenuItem value="">
                    <em>None</em>
                  </MenuItem>
                  {simulations.map((sim) => (
                    <MenuItem key={sim.id} value={sim.id}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Chip 
                          label={sim.status} 
                          size="small" 
                          color={statusColors[sim.status]}
                        />
                        {sim.name}
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenTodoDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleCreateTodo} 
            variant="contained" 
            disabled={!newTodo.title.trim()}
          >
            Create Task
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}

export default SimulationDashboard
