import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  CardActionArea,
  Typography,
  Grid,
  Chip,
  TextField,
  InputAdornment,
  ToggleButton,
  ToggleButtonGroup,
  Skeleton,
  Alert,
  Collapse,
  IconButton,
} from '@mui/material'
import {
  Search as SearchIcon,
  BatteryFull as BatteryIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material'
import { pybammApi } from '../services/api'

export interface ParameterSetInfo {
  full_name: string
  chemistry: string
  cell_type: string
  cell_format?: string
  reference?: string
  doi?: string
  key_parameters?: Record<string, number | string>
  validated_conditions?: {
    temperature_range?: string
    c_rate_range?: string
  }
  special_features?: string[]
}

interface ParameterSetSelectorProps {
  value: string | null
  onChange: (parameterSet: string, info: ParameterSetInfo) => void
  chemistryFilter?: string | null
}

const CHEMISTRY_COLORS: Record<string, 'primary' | 'secondary' | 'success' | 'warning' | 'info' | 'error'> = {
  NMC: 'primary',
  LFP: 'success',
  NCA: 'warning',
  LCO: 'info',
  SODIUM_ION: 'secondary',
  LEAD_ACID: 'error',
}

const ParameterSetSelector = ({ value, onChange, chemistryFilter }: ParameterSetSelectorProps) => {
  const [parameterSets, setParameterSets] = useState<Record<string, ParameterSetInfo> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedChemistry, setSelectedChemistry] = useState<string | null>(chemistryFilter || null)
  const [expandedSet, setExpandedSet] = useState<string | null>(null)

  useEffect(() => {
    loadParameterSets()
  }, [])

  useEffect(() => {
    if (chemistryFilter !== undefined) {
      setSelectedChemistry(chemistryFilter)
    }
  }, [chemistryFilter])

  const loadParameterSets = async () => {
    try {
      setLoading(true)
      const data = await pybammApi.getParameterSets()
      // Map API response to our extended info type
      setParameterSets(data as unknown as Record<string, ParameterSetInfo>)
    } catch (err) {
      setError('Failed to load parameter sets')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const getFilteredSets = () => {
    if (!parameterSets) return []

    return Object.entries(parameterSets).filter(([name, info]) => {
      // Filter by chemistry
      if (selectedChemistry && info.chemistry !== selectedChemistry) {
        return false
      }
      // Filter by search query
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        return (
          name.toLowerCase().includes(query) ||
          info.full_name?.toLowerCase().includes(query) ||
          info.chemistry?.toLowerCase().includes(query) ||
          info.cell_format?.toLowerCase().includes(query)
        )
      }
      return true
    })
  }

  const getUniqueChemistries = () => {
    if (!parameterSets) return []
    const chemistries = new Set(Object.values(parameterSets).map(p => p.chemistry))
    return Array.from(chemistries).filter(Boolean)
  }

  const handleSelect = (name: string, info: ParameterSetInfo) => {
    onChange(name, info)
  }

  const toggleExpand = (name: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setExpandedSet(expandedSet === name ? null : name)
  }

  if (loading) {
    return (
      <Box>
        <Skeleton variant="rectangular" height={48} sx={{ mb: 2 }} />
        <Grid container spacing={2}>
          {[1, 2, 3, 4, 5, 6].map(i => (
            <Grid item xs={12} sm={6} md={4} key={i}>
              <Skeleton variant="rectangular" height={140} />
            </Grid>
          ))}
        </Grid>
      </Box>
    )
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>
  }

  const filteredSets = getFilteredSets()
  const chemistries = getUniqueChemistries()

  return (
    <Box>
      {/* Filters */}
      <Box sx={{ mb: 3 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Search parameter sets..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{ mb: 2 }}
        />

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <Typography variant="body2" color="text.secondary">
            Chemistry:
          </Typography>
          <ToggleButtonGroup
            value={selectedChemistry}
            exclusive
            onChange={(_, v) => setSelectedChemistry(v || null)}
            size="small"
          >
            <ToggleButton value="">All</ToggleButton>
            {chemistries.map(chem => (
              <ToggleButton key={chem} value={chem}>
                {chem}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Box>
      </Box>

      {/* Parameter Set Cards */}
      <Grid container spacing={2}>
        {filteredSets.length === 0 ? (
          <Grid item xs={12}>
            <Alert severity="info">
              No parameter sets found matching your filters.
            </Alert>
          </Grid>
        ) : (
          filteredSets.map(([name, info]) => (
            <Grid item xs={12} sm={6} md={4} key={name}>
              <Card
                variant={value === name ? 'elevation' : 'outlined'}
                sx={{
                  border: value === name ? '2px solid' : undefined,
                  borderColor: value === name ? 'primary.main' : undefined,
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                }}
              >
                <CardActionArea
                  onClick={() => handleSelect(name, info)}
                  sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', alignItems: 'stretch' }}
                >
                  <CardContent sx={{ flexGrow: 1, pb: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <BatteryIcon color="action" fontSize="small" />
                        <Typography variant="subtitle1" fontWeight="bold">
                          {name}
                        </Typography>
                      </Box>
                      <Chip
                        label={info.chemistry}
                        size="small"
                        color={CHEMISTRY_COLORS[info.chemistry] || 'default'}
                      />
                    </Box>

                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {info.cell_format || info.cell_type}
                    </Typography>

                    {info.key_parameters && (
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 1 }}>
                        {info.key_parameters['Nominal cell capacity [A.h]'] && (
                          <Chip
                            label={`${info.key_parameters['Nominal cell capacity [A.h]']} Ah`}
                            size="small"
                            variant="outlined"
                          />
                        )}
                        {info.validated_conditions?.c_rate_range && (
                          <Chip
                            label={info.validated_conditions.c_rate_range}
                            size="small"
                            variant="outlined"
                          />
                        )}
                      </Box>
                    )}

                    {info.special_features && info.special_features.length > 0 && (
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                        {info.special_features.slice(0, 2).map((feature, i) => (
                          <Chip
                            key={i}
                            label={feature}
                            size="small"
                            variant="outlined"
                            color="secondary"
                            sx={{ fontSize: '0.7rem' }}
                          />
                        ))}
                        {info.special_features.length > 2 && (
                          <Chip
                            label={`+${info.special_features.length - 2}`}
                            size="small"
                            variant="outlined"
                            sx={{ fontSize: '0.7rem' }}
                          />
                        )}
                      </Box>
                    )}
                  </CardContent>
                </CardActionArea>

                {/* Expandable Details */}
                <Box sx={{ px: 2, pb: 1 }}>
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      cursor: 'pointer',
                    }}
                    onClick={(e) => toggleExpand(name, e)}
                  >
                    <Typography variant="caption" color="text.secondary">
                      Details
                    </Typography>
                    <IconButton size="small">
                      {expandedSet === name ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                    </IconButton>
                  </Box>

                  <Collapse in={expandedSet === name}>
                    <Box sx={{ pt: 1 }}>
                      {info.reference && (
                        <Typography variant="caption" display="block" color="text.secondary">
                          <strong>Reference:</strong> {info.reference}
                        </Typography>
                      )}
                      {info.validated_conditions?.temperature_range && (
                        <Typography variant="caption" display="block" color="text.secondary">
                          <strong>Temp range:</strong> {info.validated_conditions.temperature_range}
                        </Typography>
                      )}
                      {info.key_parameters && (
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="caption" color="text.secondary">
                            <strong>Key parameters:</strong>
                          </Typography>
                          <Box sx={{ pl: 1 }}>
                            {Object.entries(info.key_parameters).slice(0, 5).map(([key, val]) => (
                              <Typography key={key} variant="caption" display="block" color="text.secondary">
                                {key}: {typeof val === 'number' ? val.toExponential(2) : val}
                              </Typography>
                            ))}
                          </Box>
                        </Box>
                      )}
                    </Box>
                  </Collapse>
                </Box>
              </Card>
            </Grid>
          ))
        )}
      </Grid>

      {/* Selected Info */}
      {value && parameterSets?.[value] && (
        <Alert severity="success" sx={{ mt: 2 }} icon={<BatteryIcon />}>
          <strong>Selected:</strong> {parameterSets[value].full_name || value} ({parameterSets[value].chemistry})
        </Alert>
      )}
    </Box>
  )
}

export default ParameterSetSelector
