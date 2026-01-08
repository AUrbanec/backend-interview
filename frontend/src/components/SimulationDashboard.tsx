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
import { fetchPresets, Preset } from '../redux/slices/presetsSlice'
import { fetchTodos, createTodo, updateTodo, deleteTodo, Todo } from '../redux/slices/todosSlice'
import { AppDispatch, RootState } from '../redux/store/store'
import { useAuthContext } from '../auth/hooks'
import { usageApi } from '../services/api'
import SimulationChart from './SimulationChart'
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
  const [selectedSimulation, setSelectedSimulation] = useState<Simulation | null>(null)
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
    c_rate: 1.0,
    temperature_celsius: 25.0,
    cycles: 1,
  })

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
      await dispatch(createSimulation(newSim))
      setNewSim({
        name: '',
        description: '',
        chemistry: 'LFP',
        c_rate: 1.0,
        temperature_celsius: 25.0,
        cycles: 1,
      })
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
    setSelectedSimulation(simulation)
    setTabValue(1)
  }

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
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
            <Typography variant="h5">My Simulations</Typography>
            <Box>
              <Button
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={() => dispatch(fetchSimulations())}
                sx={{ mr: 1 }}
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
                    <Card>
                      <CardContent>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                          <Typography variant="h6" noWrap sx={{ maxWidth: '70%' }}>
                            {sim.name}
                          </Typography>
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
          {selectedSimulation?.results ? (
            <SimulationChart simulation={selectedSimulation} />
          ) : (
            <Alert severity="info">
              Select a completed simulation from the Simulations tab to view results.
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
                                    setSelectedSimulation(sim)
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
              <Typography gutterBottom>C-Rate: {newSim.c_rate}C</Typography>
              <Slider
                value={newSim.c_rate}
                onChange={(_, v) => setNewSim({ ...newSim, c_rate: v as number })}
                min={0.1}
                max={5}
                step={0.1}
                marks={[
                  { value: 0.5, label: '0.5C' },
                  { value: 1, label: '1C' },
                  { value: 2, label: '2C' },
                  { value: 5, label: '5C' },
                ]}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography gutterBottom>Temperature: {newSim.temperature_celsius}°C</Typography>
              <Slider
                value={newSim.temperature_celsius}
                onChange={(_, v) => setNewSim({ ...newSim, temperature_celsius: v as number })}
                min={-10}
                max={60}
                step={1}
                marks={[
                  { value: 0, label: '0°C' },
                  { value: 25, label: '25°C' },
                  { value: 45, label: '45°C' },
                ]}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <Typography gutterBottom>Cycles: {newSim.cycles}</Typography>
              <Slider
                value={newSim.cycles}
                onChange={(_, v) => setNewSim({ ...newSim, cycles: v as number })}
                min={1}
                max={50}
                step={1}
                marks={[
                  { value: 1, label: '1' },
                  { value: 10, label: '10' },
                  { value: 25, label: '25' },
                  { value: 50, label: '50' },
                ]}
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
