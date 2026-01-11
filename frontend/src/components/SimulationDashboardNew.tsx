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
  CircularProgress,
  LinearProgress,
  AppBar,
  Toolbar,
  Alert,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Checkbox,
  Link as MuiLink,
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
  Assignment as AssignmentIcon,
  BatteryFull as BatteryIcon,
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
  CreateSimulationParams,
} from '../redux/slices/simulationsSlice'
import { fetchPresets } from '../redux/slices/presetsSlice'
import { fetchTodos, createTodo, updateTodo, deleteTodo, Todo } from '../redux/slices/todosSlice'
import { AppDispatch, RootState } from '../redux/store/store'
import { useAuthContext } from '../auth/hooks'
import { usageApi } from '../services/api'
import SimulationChart from './SimulationChart'
import PyBAMMReference from './PyBAMMReference'
import SimulationWizard, { SimulationWizardData } from './SimulationWizard'
import ParameterSetSelector from './ParameterSetSelector'

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

const SimulationDashboard = () => {
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const { user } = useAuthContext()
  const { simulations, loading } = useSelector((state: RootState) => state.simulations)
  const { todos, loading: todosLoading } = useSelector((state: RootState) => state.todos)
  
  const [tabValue, setTabValue] = useState(0)
  const [openWizard, setOpenWizard] = useState(false)
  const [openTodoDialog, setOpenTodoDialog] = useState(false)
  const [selectedSimulations, setSelectedSimulations] = useState<Simulation[]>([])
  const [creatingSimulation, setCreatingSimulation] = useState(false)
  const [usageData, setUsageData] = useState<{
    simulations_count: number
    simulations_limit: number
    usage_percentage: number
  } | null>(null)

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

  const handleCreateSimulation = async (wizardData: SimulationWizardData) => {
    setCreatingSimulation(true)
    try {
      // Build the simulation params from wizard data
      const params: CreateSimulationParams = {
        name: wizardData.name,
        description: wizardData.description || undefined,
        parameter_set: wizardData.parameterSet || undefined,
        chemistry: wizardData.chemistry as BatteryChemistry,
        model_type: wizardData.modelType,
        model_options: Object.keys(wizardData.modelOptions).length > 0 
          ? wizardData.modelOptions as Record<string, string>
          : undefined,
        protocol: wizardData.protocol,
        c_rate: wizardData.cRate,
        temperature_celsius: wizardData.temperatureCelsius,
        cycles: wizardData.cycles,
        experiment_mode: wizardData.experimentMode,
        experiment_definition: wizardData.experimentMode === 'custom' 
          ? wizardData.experimentDefinition || undefined 
          : undefined,
        experiment_template_id: wizardData.experimentMode === 'template'
          ? wizardData.experimentTemplateId || undefined
          : undefined,
        also_run_with_model: wizardData.alsoRunWithModel || undefined,
      }

      await dispatch(createSimulation(params))
      setOpenWizard(false)
      loadUsage()
    } catch (error) {
      console.error('Failed to create simulation:', error)
    } finally {
      setCreatingSimulation(false)
    }
  }

  const handleDeleteSimulation = async (id: string) => {
    await dispatch(deleteSimulation(id))
  }

  const handleCancelSimulation = async (id: string) => {
    await dispatch(cancelSimulation(id))
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
          <Tab label="Parameter Sets" icon={<BatteryIcon />} iconPosition="start" />
          <Tab label="Tasks" icon={<AssignmentIcon />} iconPosition="start" />
          <Tab label="PyBAMM Reference" icon={<ScienceIcon />} iconPosition="start" />
        </Tabs>

        {/* Simulations Tab */}
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
                onClick={() => setOpenWizard(true)}
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
                          {sim.parameter_set && (
                            <Typography variant="caption" display="block">
                              <strong>Parameter Set:</strong> {sim.parameter_set}
                            </Typography>
                          )}
                          <Typography variant="caption" display="block">
                            <strong>Chemistry:</strong> {sim.chemistry}
                          </Typography>
                          {sim.model_type && (
                            <Typography variant="caption" display="block">
                              <strong>Model:</strong> {sim.model_type}
                            </Typography>
                          )}
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

        {/* Results Viewer Tab */}
        <TabPanel value={tabValue} index={1}>
          {selectedSimulations.length > 0 && selectedSimulations.some(s => s.results) ? (
            <SimulationChart simulations={selectedSimulations} />
          ) : (
            <Alert severity="info">
              Select one or more completed simulations from the Simulations tab to view and compare results.
            </Alert>
          )}
        </TabPanel>

        {/* Parameter Sets Tab */}
        <TabPanel value={tabValue} index={2}>
          <Typography variant="h5" gutterBottom>
            Available Parameter Sets
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Browse validated PyBaMM parameter sets for different battery cells. These contain experimentally
            measured parameters that you can use in your simulations.
          </Typography>
          <ParameterSetSelector
            value={null}
            onChange={(name, info) => {
              console.log('Selected parameter set:', name, info)
            }}
          />
        </TabPanel>

        {/* Tasks Tab */}
        <TabPanel value={tabValue} index={3}>
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
        <TabPanel value={tabValue} index={4}>
          <PyBAMMReference />
        </TabPanel>
      </Container>

      {/* Simulation Wizard Dialog */}
      <SimulationWizard
        open={openWizard}
        onClose={() => setOpenWizard(false)}
        onSubmit={handleCreateSimulation}
        loading={creatingSimulation}
      />

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
