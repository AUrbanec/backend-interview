import { useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  Grid,
  Card,
  CardContent,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Alert,
  AlertTitle,
} from '@mui/material'
import { 
  Download as DownloadIcon,
  ExpandMore as ExpandMoreIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Thermostat as ThermostatIcon,
} from '@mui/icons-material'
import { Simulation } from '../redux/slices/simulationsSlice'

interface SimulationChartProps {
  simulation?: Simulation
  simulations?: Simulation[]
}

type ChartType = 'voltage' | 'current' | 'capacity' | 'soc' | 'temperature' | 'power'

const CHART_COLORS = [
  '#2196f3', '#f44336', '#4caf50', '#ff9800', '#9c27b0',
  '#00bcd4', '#e91e63', '#8bc34a', '#ff5722', '#673ab7'
]

const SimulationChart = ({ simulation, simulations }: SimulationChartProps) => {
  const [chartType, setChartType] = useState<ChartType>('voltage')
  
  // Support both single simulation and multiple simulations
  const allSimulations = simulations || (simulation ? [simulation] : [])
  const validSimulations = allSimulations.filter(s => s.results)
  
  if (validSimulations.length === 0) {
    return <Typography>No results available</Typography>
  }

  // Use first simulation for shared data structure checks
  const firstResults = validSimulations[0].results!
  const { discharge_capacity_ah, soc, temperature_celsius, power_w, step_metrics, summary } = firstResults

  const getChartDataForSim = (sim: Simulation, colorIndex: number): { data: number[]; timeHours: number[]; label: string; color: string; name: string } | null => {
    const results = sim.results
    if (!results) return null
    
    const color = CHART_COLORS[colorIndex % CHART_COLORS.length]
    const timeHours = results.time_seconds.map((t: number) => t / 3600)
    
    let data: number[]
    let label: string
    
    switch (chartType) {
      case 'voltage':
        data = results.voltage_v
        label = 'Voltage (V)'
        break
      case 'current':
        data = results.current_a
        label = 'Current (A)'
        break
      case 'capacity':
        data = results.discharge_capacity_ah || []
        label = 'Capacity (Ah)'
        break
      case 'soc':
        data = results.soc || []
        label = 'State of Charge'
        break
      case 'temperature':
        data = results.temperature_celsius || []
        label = 'Temperature (°C)'
        break
      case 'power':
        data = results.power_w || []
        label = 'Power (W)'
        break
      default:
        data = results.voltage_v
        label = 'Voltage (V)'
    }
    
    return { data, timeHours, label, color, name: sim.name }
  }

  const allChartData = validSimulations.map((sim, i) => getChartDataForSim(sim, i)).filter(Boolean) as NonNullable<ReturnType<typeof getChartDataForSim>>[]

  // Simple SVG chart rendering with multiple datasets
  const renderChart = () => {
    const datasetsWithData = allChartData.filter(d => d.data.length > 0)
    if (datasetsWithData.length === 0) {
      return <Typography color="text.secondary">No data available for this chart type</Typography>
    }

    const width = 800
    const height = 400
    const padding = 60
    const legendHeight = validSimulations.length > 1 ? 40 : 0
    const chartWidth = width - padding * 2
    const chartHeight = height - padding * 2 - legendHeight

    // Calculate global min/max across all datasets
    const allTimeHours = datasetsWithData.flatMap(d => d.timeHours)
    const allValues = datasetsWithData.flatMap(d => d.data)
    const maxTime = Math.max(...allTimeHours)
    const minVal = Math.min(...allValues)
    const maxVal = Math.max(...allValues)
    const valRange = maxVal - minVal || 1

    // Generate polyline points for each dataset
    const datasetLines = datasetsWithData.map(dataset => {
      const step = Math.max(1, Math.floor(dataset.data.length / 500))
      const points = dataset.data
        .filter((_, i) => i % step === 0)
        .map((val, i) => {
          const actualIndex = i * step
          const x = padding + (dataset.timeHours[actualIndex] / maxTime) * chartWidth
          const y = padding + chartHeight - ((val - minVal) / valRange) * chartHeight
          return `${x},${y}`
        }).join(' ')
      return { ...dataset, points }
    })

    return (
      <svg width={width} height={height + legendHeight} style={{ maxWidth: '100%', height: 'auto' }}>
        {/* Background */}
        <rect x={padding} y={padding} width={chartWidth} height={chartHeight} fill="#fafafa" />
        
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((fraction) => (
          <g key={fraction}>
            <line
              x1={padding}
              y1={padding + chartHeight * fraction}
              x2={padding + chartWidth}
              y2={padding + chartHeight * fraction}
              stroke="#e0e0e0"
              strokeDasharray="4"
            />
            <text
              x={padding - 10}
              y={padding + chartHeight * fraction + 4}
              textAnchor="end"
              fontSize="12"
              fill="#666"
            >
              {(maxVal - fraction * valRange).toFixed(2)}
            </text>
          </g>
        ))}

        {/* X-axis labels */}
        {[0, 0.25, 0.5, 0.75, 1].map((fraction) => (
          <text
            key={`x-${fraction}`}
            x={padding + chartWidth * fraction}
            y={height - legendHeight - 20}
            textAnchor="middle"
            fontSize="12"
            fill="#666"
          >
            {(maxTime * fraction).toFixed(2)}h
          </text>
        ))}

        {/* Data lines for each simulation */}
        {datasetLines.map((dataset, idx) => (
          <polyline
            key={idx}
            points={dataset.points}
            fill="none"
            stroke={dataset.color}
            strokeWidth="2"
          />
        ))}

        {/* Axis labels */}
        <text
          x={width / 2}
          y={height - legendHeight - 5}
          textAnchor="middle"
          fontSize="14"
          fill="#333"
        >
          Time (hours)
        </text>
        <text
          x={15}
          y={(height - legendHeight) / 2}
          textAnchor="middle"
          fontSize="14"
          fill="#333"
          transform={`rotate(-90, 15, ${(height - legendHeight) / 2})`}
        >
          {datasetsWithData[0]?.label || ''}
        </text>

        {/* Legend for multiple simulations */}
        {validSimulations.length > 1 && (
          <g transform={`translate(${padding}, ${height - 10})`}>
            {datasetLines.map((dataset, idx) => (
              <g key={idx} transform={`translate(${idx * 150}, 0)`}>
                <line x1="0" y1="0" x2="20" y2="0" stroke={dataset.color} strokeWidth="3" />
                <text x="25" y="4" fontSize="12" fill="#333">
                  {dataset.name.length > 15 ? dataset.name.substring(0, 15) + '...' : dataset.name}
                </text>
              </g>
            ))}
          </g>
        )}
      </svg>
    )
  }

  const handleExport = (format: 'csv' | 'json') => {
    // Export all selected simulations
    const exportData = validSimulations.map(sim => ({
      name: sim.name,
      chemistry: sim.chemistry,
      c_rate: sim.c_rate,
      results: sim.results
    }))
    
    let content: string
    let filename: string
    let mimeType: string
    const namePrefix = validSimulations.length === 1 
      ? validSimulations[0].name.replace(/\s+/g, '_')
      : 'comparison'

    if (format === 'csv') {
      // For multi-simulation CSV, include simulation name as prefix
      const allRows: string[] = []
      validSimulations.forEach(sim => {
        const results = sim.results!
        const headers = ['simulation', 'time_seconds', 'voltage_v', 'current_a']
        if (results.discharge_capacity_ah) headers.push('discharge_capacity_ah')
        
        if (allRows.length === 0) {
          allRows.push(headers.join(','))
        }
        
        results.time_seconds.forEach((t: number, i: number) => {
          const row: (string | number)[] = [sim.name, t, results.voltage_v[i], results.current_a[i]]
          if (results.discharge_capacity_ah) row.push(results.discharge_capacity_ah[i])
          allRows.push(row.join(','))
        })
      })
      
      content = allRows.join('\n')
      filename = `${namePrefix}_results.csv`
      mimeType = 'text/csv'
    } else {
      content = JSON.stringify(exportData, null, 2)
      filename = `${namePrefix}_results.json`
      mimeType = 'application/json'
    }

    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  // Safety alerts helper
  const renderSafetyAlerts = () => {
    const safetyEvents = summary.safety_events || []
    const hasCritical = summary.max_temp_exceeded || summary.voltage_violation
    const hasWarnings = safetyEvents.some(e => e.severity === 'warning')
    
    if (!hasCritical && !hasWarnings && safetyEvents.length === 0) return null
    
    return (
      <Box sx={{ mb: 3 }}>
        {summary.max_temp_exceeded && (
          <Alert severity="error" icon={<ErrorIcon />} sx={{ mb: 1 }}>
            <AlertTitle>Critical Temperature Exceeded</AlertTitle>
            Max temperature reached {summary.max_temperature_celsius?.toFixed(1)}°C - 
            exceeds critical threshold of {summary.thermal_thresholds?.max_temp_critical_celsius}°C
          </Alert>
        )}
        {summary.voltage_violation && (
          <Alert severity="error" icon={<ErrorIcon />} sx={{ mb: 1 }}>
            <AlertTitle>Voltage Violation Detected</AlertTitle>
            Voltage exceeded safe operating limits during simulation
          </Alert>
        )}
        {safetyEvents.filter(e => e.severity === 'warning').map((event, idx) => (
          <Alert key={idx} severity="warning" icon={<WarningIcon />} sx={{ mb: 1 }}>
            {event.message}
          </Alert>
        ))}
      </Box>
    )
  }

  return (
    <Box>
      {/* Safety Alerts */}
      {renderSafetyAlerts()}
      
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h5">
            {validSimulations.length === 1 
              ? `${validSimulations[0].name} - Results` 
              : `Comparing ${validSimulations.length} Simulations`}
          </Typography>
          <Box>
            <Button
              startIcon={<DownloadIcon />}
              onClick={() => handleExport('csv')}
              sx={{ mr: 1 }}
            >
              Export CSV
            </Button>
            <Button
              startIcon={<DownloadIcon />}
              onClick={() => handleExport('json')}
            >
              Export JSON
            </Button>
          </Box>
        </Box>

        <ToggleButtonGroup
          value={chartType}
          exclusive
          onChange={(_, value) => value && setChartType(value)}
          sx={{ mb: 3, flexWrap: 'wrap' }}
        >
          <ToggleButton value="voltage">Voltage</ToggleButton>
          <ToggleButton value="current">Current</ToggleButton>
          <ToggleButton value="capacity" disabled={!discharge_capacity_ah}>
            Capacity
          </ToggleButton>
          <ToggleButton value="soc" disabled={!soc}>
            SOC
          </ToggleButton>
          <ToggleButton value="temperature" disabled={!temperature_celsius}>
            Temperature
          </ToggleButton>
          <ToggleButton value="power" disabled={!power_w}>
            Power
          </ToggleButton>
        </ToggleButtonGroup>

        <Box sx={{ overflowX: 'auto' }}>
          {renderChart()}
        </Box>
      </Paper>

      {/* Summary Stats */}
      <Grid container spacing={2}>
        <Grid item xs={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Chemistry
              </Typography>
              <Typography variant="h5">{summary.chemistry}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                C-Rate
              </Typography>
              <Typography variant="h5">{summary.c_rate}C</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Max Voltage
              </Typography>
              <Typography variant="h5">{summary.max_voltage.toFixed(3)} V</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Min Voltage
              </Typography>
              <Typography variant="h5">{summary.min_voltage.toFixed(3)} V</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Temperature
              </Typography>
              <Typography variant="h5">{summary.temperature_celsius}°C</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Cycles
              </Typography>
              <Typography variant="h5">{summary.cycles}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Total Time
              </Typography>
              <Typography variant="h5">{summary.total_time_hours.toFixed(2)} hrs</Typography>
            </CardContent>
          </Card>
        </Grid>
        {summary.total_capacity_ah && (
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Total Capacity
                </Typography>
                <Typography variant="h5">{summary.total_capacity_ah.toFixed(3)} Ah</Typography>
              </CardContent>
            </Card>
          </Grid>
        )}
        {summary.protocol_type && (
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Protocol
                </Typography>
                <Chip label={summary.protocol_type} color="primary" />
              </CardContent>
            </Card>
          </Grid>
        )}
        {summary.total_delivered_wh !== undefined && (
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Energy Delivered
                </Typography>
                <Typography variant="h5">{summary.total_delivered_wh.toFixed(2)} Wh</Typography>
              </CardContent>
            </Card>
          </Grid>
        )}
        {summary.max_power_w !== undefined && (
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Max Power
                </Typography>
                <Typography variant="h5">{summary.max_power_w.toFixed(2)} W</Typography>
              </CardContent>
            </Card>
          </Grid>
        )}
        {summary.final_soc !== undefined && (
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Final SOC
                </Typography>
                <Typography variant="h5">{(summary.final_soc * 100).toFixed(1)}%</Typography>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>

      {/* Thermal Analysis Section */}
      {summary.thermal_mode && (
        <Accordion sx={{ mt: 3 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <ThermostatIcon color="primary" />
              <Typography variant="h6">Thermal Analysis</Typography>
              <Chip 
                label={summary.thermal_mode === 'lumped' ? 'Dynamic' : 'Isothermal'} 
                size="small" 
                color={summary.thermal_mode === 'lumped' ? 'primary' : 'default'}
              />
              {summary.max_temp_exceeded && (
                <Chip label="CRITICAL" size="small" color="error" />
              )}
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              {summary.max_temperature_celsius !== undefined && (
                <Grid item xs={6} md={3}>
                  <Card sx={{ bgcolor: summary.max_temp_exceeded ? 'error.light' : undefined }}>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Max Temperature
                      </Typography>
                      <Typography variant="h5">
                        {summary.max_temperature_celsius.toFixed(1)}°C
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              )}
              {summary.min_temperature_celsius !== undefined && (
                <Grid item xs={6} md={3}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Min Temperature
                      </Typography>
                      <Typography variant="h5">
                        {summary.min_temperature_celsius.toFixed(1)}°C
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              )}
              {summary.avg_temperature_celsius !== undefined && (
                <Grid item xs={6} md={3}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Avg Temperature
                      </Typography>
                      <Typography variant="h5">
                        {summary.avg_temperature_celsius.toFixed(1)}°C
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              )}
              {summary.time_above_warning_seconds !== undefined && summary.time_above_warning_seconds > 0 && (
                <Grid item xs={6} md={3}>
                  <Card sx={{ bgcolor: 'warning.light' }}>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Time Above Warning
                      </Typography>
                      <Typography variant="h5">
                        {(summary.time_above_warning_seconds / 60).toFixed(1)} min
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              )}
              {summary.time_above_critical_seconds !== undefined && summary.time_above_critical_seconds > 0 && (
                <Grid item xs={6} md={3}>
                  <Card sx={{ bgcolor: 'error.light' }}>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Time Above Critical
                      </Typography>
                      <Typography variant="h5">
                        {(summary.time_above_critical_seconds / 60).toFixed(1)} min
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              )}
              {summary.max_heat_generation_w_m3 !== undefined && (
                <Grid item xs={6} md={3}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Max Heat Generation
                      </Typography>
                      <Typography variant="h5">
                        {(summary.max_heat_generation_w_m3 / 1000).toFixed(1)} kW/m³
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              )}
              {summary.thermal_thresholds && (
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary">
                    Thresholds: Warning at {summary.thermal_thresholds.max_temp_warning_celsius}°C, 
                    Critical at {summary.thermal_thresholds.max_temp_critical_celsius}°C
                  </Typography>
                </Grid>
              )}
            </Grid>
          </AccordionDetails>
        </Accordion>
      )}

      {/* Step Metrics Table */}
      {step_metrics && step_metrics.length > 0 && (
        <Accordion sx={{ mt: 3 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">Step-by-Step Analysis ({step_metrics.length} steps)</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Step</TableCell>
                    <TableCell align="right">Duration (s)</TableCell>
                    <TableCell align="right">Avg Current (A)</TableCell>
                    <TableCell align="right">Start V</TableCell>
                    <TableCell align="right">End V</TableCell>
                    <TableCell align="right">Ah</TableCell>
                    <TableCell align="right">Wh</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {step_metrics.map((step) => (
                    <TableRow key={step.step_number}>
                      <TableCell>{step.step_number}</TableCell>
                      <TableCell align="right">{step.duration_seconds.toFixed(1)}</TableCell>
                      <TableCell align="right">{step.average_current_a.toFixed(3)}</TableCell>
                      <TableCell align="right">{step.start_voltage_v?.toFixed(3) ?? '-'}</TableCell>
                      <TableCell align="right">{step.end_voltage_v?.toFixed(3) ?? '-'}</TableCell>
                      <TableCell align="right">{step.delivered_ah.toFixed(4)}</TableCell>
                      <TableCell align="right">{step.delivered_wh.toFixed(4)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </AccordionDetails>
        </Accordion>
      )}
    </Box>
  )
}

export default SimulationChart
