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
} from '@mui/material'
import { Download as DownloadIcon } from '@mui/icons-material'
import { Simulation } from '../redux/slices/simulationsSlice'

interface SimulationChartProps {
  simulation: Simulation
}

type ChartType = 'voltage' | 'current' | 'capacity'

const SimulationChart = ({ simulation }: SimulationChartProps) => {
  const [chartType, setChartType] = useState<ChartType>('voltage')
  
  const results = simulation.results
  if (!results) {
    return <Typography>No results available</Typography>
  }

  const { time_seconds, voltage_v, current_a, discharge_capacity_ah, summary } = results

  const getChartData = () => {
    switch (chartType) {
      case 'voltage':
        return { data: voltage_v, label: 'Voltage (V)', color: '#2196f3' }
      case 'current':
        return { data: current_a, label: 'Current (A)', color: '#f44336' }
      case 'capacity':
        return { data: discharge_capacity_ah || [], label: 'Capacity (Ah)', color: '#4caf50' }
    }
  }

  const chartData = getChartData()
  const timeHours = time_seconds.map(t => t / 3600)

  // Simple SVG chart rendering
  const renderChart = () => {
    if (chartData.data.length === 0) {
      return <Typography color="text.secondary">No data available for this chart type</Typography>
    }

    const width = 800
    const height = 400
    const padding = 60
    const chartWidth = width - padding * 2
    const chartHeight = height - padding * 2

    const maxTime = Math.max(...timeHours)
    const minVal = Math.min(...chartData.data)
    const maxVal = Math.max(...chartData.data)
    const valRange = maxVal - minVal || 1

    const points = chartData.data.map((val, i) => {
      const x = padding + (timeHours[i] / maxTime) * chartWidth
      const y = padding + chartHeight - ((val - minVal) / valRange) * chartHeight
      return `${x},${y}`
    }).join(' ')

    // Sample points for performance (max 500 points)
    const step = Math.max(1, Math.floor(chartData.data.length / 500))
    const sampledPoints = chartData.data
      .filter((_, i) => i % step === 0)
      .map((val, i) => {
        const actualIndex = i * step
        const x = padding + (timeHours[actualIndex] / maxTime) * chartWidth
        const y = padding + chartHeight - ((val - minVal) / valRange) * chartHeight
        return `${x},${y}`
      }).join(' ')

    return (
      <svg width={width} height={height} style={{ maxWidth: '100%', height: 'auto' }}>
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
            y={height - 20}
            textAnchor="middle"
            fontSize="12"
            fill="#666"
          >
            {(maxTime * fraction).toFixed(2)}h
          </text>
        ))}

        {/* Data line */}
        <polyline
          points={sampledPoints}
          fill="none"
          stroke={chartData.color}
          strokeWidth="2"
        />

        {/* Axis labels */}
        <text
          x={width / 2}
          y={height - 5}
          textAnchor="middle"
          fontSize="14"
          fill="#333"
        >
          Time (hours)
        </text>
        <text
          x={15}
          y={height / 2}
          textAnchor="middle"
          fontSize="14"
          fill="#333"
          transform={`rotate(-90, 15, ${height / 2})`}
        >
          {chartData.label}
        </text>
      </svg>
    )
  }

  const handleExport = (format: 'csv' | 'json') => {
    let content: string
    let filename: string
    let mimeType: string

    if (format === 'csv') {
      const headers = ['time_seconds', 'voltage_v', 'current_a']
      if (discharge_capacity_ah) headers.push('discharge_capacity_ah')
      
      const rows = time_seconds.map((t, i) => {
        const row = [t, voltage_v[i], current_a[i]]
        if (discharge_capacity_ah) row.push(discharge_capacity_ah[i])
        return row.join(',')
      })
      
      content = [headers.join(','), ...rows].join('\n')
      filename = `${simulation.name.replace(/\s+/g, '_')}_results.csv`
      mimeType = 'text/csv'
    } else {
      content = JSON.stringify(results, null, 2)
      filename = `${simulation.name.replace(/\s+/g, '_')}_results.json`
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

  return (
    <Box>
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h5">{simulation.name} - Results</Typography>
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
          sx={{ mb: 3 }}
        >
          <ToggleButton value="voltage">Voltage</ToggleButton>
          <ToggleButton value="current">Current</ToggleButton>
          <ToggleButton value="capacity" disabled={!discharge_capacity_ah}>
            Capacity
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
      </Grid>
    </Box>
  )
}

export default SimulationChart
