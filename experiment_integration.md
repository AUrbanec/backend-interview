I'll explore the existing codebase and search for PyBAMM experiment mode documentation to create a comprehensive implementation plan.



Let me use the correct WSL paths:













# PyBAMM Experiment Mode Implementation Plan

Based on my analysis of the codebase and PyBAMM documentation, here's a comprehensive plan for implementing experiment mode.

---

## Overview: What PyBAMM Experiment Mode Enables

PyBAMM's `Experiment` class allows defining complex battery test protocols using:
1. **String-based instructions**: `"Discharge at 1C until 3.3V"`, `"Rest for 1 hour"`, `"Hold at 4.1V until C/50"`
2. **Programmatic steps**: `pybamm.step.current(1, duration="1h", termination="2.5V")`
3. **Cycles**: Grouping steps into repeatable cycles using tuples
4. **Drive cycles**: Time-varying current/power/voltage profiles as 2-column arrays
5. **Step attributes**: `period`, `temperature`, `tags`, `duration`, `termination`

---

## 1. SQL Migrations

### Migration: `20240107000000_experiment_mode.sql`

```sql
-- New tables and columns needed:

-- 1. Experiment steps table for reusable step definitions
CREATE TABLE public.experiment_steps (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    name TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    
    -- Step definition
    step_type TEXT NOT NULL,  -- 'current', 'c_rate', 'voltage', 'power', 'resistance', 'rest', 'string'
    value NUMERIC,            -- For current/c_rate/voltage/power/resistance
    value_unit TEXT,          -- 'A', 'C', 'V', 'W', 'Ohm'
    
    -- Duration and termination
    duration TEXT,            -- e.g., '1 hour', '30 minutes', '3600 seconds'
    termination TEXT,         -- e.g., '3.3V', 'C/50', '50mA'
    
    -- Additional options
    period TEXT,              -- Sampling period, e.g., '1 minute'
    temperature TEXT,         -- Step-specific temperature, e.g., '25oC'
    tags TEXT[],              -- Tags for filtering/analysis
    direction TEXT,           -- 'charge', 'discharge', null
    
    -- For string-based steps
    step_string TEXT,         -- Raw string like "Discharge at 1C until 3.3V"
    
    -- For drive cycles (stored as JSON array of [time, value] pairs)
    drive_cycle_data JSONB,
    drive_cycle_type TEXT,    -- 'current', 'power', 'voltage'
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, name)
);

-- 2. Experiment templates (collections of steps grouped into cycles)
CREATE TABLE public.experiment_templates (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    name TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    
    -- Experiment structure (array of cycle definitions)
    -- Each cycle is an array of step IDs or inline step definitions
    cycles JSONB NOT NULL DEFAULT '[]',
    
    -- Default settings
    default_period TEXT DEFAULT '1 minute',
    default_temperature_celsius NUMERIC DEFAULT 25.0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, name)
);

-- 3. Drive cycle library (standard profiles like WLTP, UDDS, etc.)
CREATE TABLE public.drive_cycles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),  -- NULL = system preset
    name TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT TRUE,
    
    -- Drive cycle data
    cycle_type TEXT NOT NULL,  -- 'current', 'power', 'voltage'
    data JSONB NOT NULL,       -- Array of [time_s, value] pairs
    duration_seconds NUMERIC,
    
    -- Metadata
    source TEXT,               -- e.g., 'EPA', 'custom', 'WLTP'
    tags TEXT[],
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Add experiment_mode column to simulations table
ALTER TABLE public.simulations 
ADD COLUMN IF NOT EXISTS experiment_mode TEXT DEFAULT 'protocol';
-- Values: 'protocol' (use protocol_type), 'custom' (use experiment_definition), 'template' (use experiment_template_id)

ALTER TABLE public.simulations 
ADD COLUMN IF NOT EXISTS experiment_definition JSONB;
-- Stores custom experiment steps when experiment_mode = 'custom'

ALTER TABLE public.simulations 
ADD COLUMN IF NOT EXISTS experiment_template_id UUID REFERENCES public.experiment_templates(id);

ALTER TABLE public.simulations 
ADD COLUMN IF NOT EXISTS experiment_period TEXT DEFAULT '1 minute';

-- 5. Add to parameter_presets for experiment presets
ALTER TABLE public.parameter_presets 
ADD COLUMN IF NOT EXISTS experiment_mode TEXT DEFAULT 'protocol';

ALTER TABLE public.parameter_presets 
ADD COLUMN IF NOT EXISTS experiment_definition JSONB;

ALTER TABLE public.parameter_presets 
ADD COLUMN IF NOT EXISTS experiment_template_id UUID;

-- Indexes
CREATE INDEX idx_experiment_steps_user ON public.experiment_steps(user_id);
CREATE INDEX idx_experiment_steps_public ON public.experiment_steps(is_public) WHERE is_public = TRUE;
CREATE INDEX idx_experiment_templates_user ON public.experiment_templates(user_id);
CREATE INDEX idx_drive_cycles_user ON public.drive_cycles(user_id);
CREATE INDEX idx_simulations_experiment_mode ON public.simulations(experiment_mode);

-- RLS policies (similar pattern to existing tables)
ALTER TABLE public.experiment_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.experiment_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.drive_cycles ENABLE ROW LEVEL SECURITY;

-- ... (RLS policies follow same pattern as parameter_presets)
```

---

## 2. Backend API Changes

### 2.1 New Schemas ([backend/app/api/simulations/schemas.py](cci:7://file://wsl.localhost/Ubuntu/home/alex/backend-interview/backend/app/api/simulations/schemas.py:0:0-0:0))

```python
# Add new enums and models:

class ExperimentMode(str, Enum):
    PROTOCOL = "protocol"      # Use predefined protocol_type
    CUSTOM = "custom"          # Use custom experiment_definition
    TEMPLATE = "template"      # Use experiment_template_id

class StepType(str, Enum):
    CURRENT = "current"
    C_RATE = "c_rate"
    VOLTAGE = "voltage"
    POWER = "power"
    RESISTANCE = "resistance"
    REST = "rest"
    STRING = "string"          # Raw PyBAMM string

class ExperimentStep(BaseModel):
    step_type: StepType
    value: Optional[float] = None
    value_unit: Optional[str] = None
    duration: Optional[str] = None        # "1 hour", "30 minutes"
    termination: Optional[str] = None     # "3.3V", "C/50"
    period: Optional[str] = None
    temperature: Optional[str] = None
    tags: Optional[List[str]] = None
    direction: Optional[str] = None       # "charge", "discharge"
    step_string: Optional[str] = None     # For STRING type
    drive_cycle_data: Optional[List[List[float]]] = None  # [[time, value], ...]
    drive_cycle_type: Optional[str] = None

class ExperimentCycle(BaseModel):
    steps: List[ExperimentStep]
    repeat: int = 1

class ExperimentDefinition(BaseModel):
    cycles: List[ExperimentCycle]
    default_period: Optional[str] = "1 minute"
    default_temperature_celsius: Optional[float] = 25.0

# Update SimulationCreate to include experiment mode
class SimulationCreate(BaseModel):
    # ... existing fields ...
    experiment_mode: ExperimentMode = ExperimentMode.PROTOCOL
    experiment_definition: Optional[ExperimentDefinition] = None
    experiment_template_id: Optional[str] = None
    experiment_period: Optional[str] = "1 minute"
```

### 2.2 New Protocol Builder (`backend/app/api/simulations/experiment_builder.py`)

```python
"""
Convert ExperimentDefinition to PyBAMM Experiment steps.
Handles string-based, programmatic, and drive cycle steps.
"""

import pybamm
from typing import List, Union
from .schemas import ExperimentStep, ExperimentDefinition, StepType

def build_pybamm_step(step: ExperimentStep) -> Union[str, pybamm.step.BaseStep]:
    """Convert a single ExperimentStep to PyBAMM format"""
    
    if step.step_type == StepType.STRING:
        return step.step_string
    
    if step.step_type == StepType.REST:
        return f"Rest for {step.duration}"
    
    # Build kwargs for programmatic steps
    kwargs = {}
    if step.duration:
        kwargs["duration"] = step.duration
    if step.termination:
        kwargs["termination"] = step.termination
    if step.period:
        kwargs["period"] = step.period
    if step.temperature:
        kwargs["temperature"] = step.temperature
    if step.tags:
        kwargs["tags"] = step.tags
    
    # Handle drive cycle data
    if step.drive_cycle_data:
        import numpy as np
        data = np.array(step.drive_cycle_data)
        
        if step.step_type == StepType.CURRENT:
            return pybamm.step.current(data, **kwargs)
        elif step.step_type == StepType.POWER:
            return pybamm.step.power(data, **kwargs)
        elif step.step_type == StepType.VOLTAGE:
            return pybamm.step.voltage(data, **kwargs)
    
    # Handle regular steps
    value = step.value
    if step.step_type == StepType.CURRENT:
        return pybamm.step.current(value, **kwargs)
    elif step.step_type == StepType.C_RATE:
        return pybamm.step.c_rate(value, **kwargs)
    elif step.step_type == StepType.VOLTAGE:
        return pybamm.step.voltage(value, **kwargs)
    elif step.step_type == StepType.POWER:
        return pybamm.step.power(value, **kwargs)
    elif step.step_type == StepType.RESISTANCE:
        return pybamm.step.resistance(value, **kwargs)
    
    raise ValueError(f"Unknown step type: {step.step_type}")

def build_experiment_from_definition(definition: ExperimentDefinition) -> List:
    """Convert ExperimentDefinition to PyBAMM Experiment steps list"""
    
    experiment_steps = []
    
    for cycle in definition.cycles:
        cycle_steps = tuple(build_pybamm_step(step) for step in cycle.steps)
        
        if cycle.repeat > 1:
            experiment_steps.extend([cycle_steps] * cycle.repeat)
        else:
            experiment_steps.append(cycle_steps)
    
    return experiment_steps
```

### 2.3 Update Simulation Runner ([backend/app/api/simulations/simulation_runner.py](cci:7://file://wsl.localhost/Ubuntu/home/alex/backend-interview/backend/app/api/simulations/simulation_runner.py:0:0-0:0))

Add logic to handle `experiment_mode`:
- If `experiment_mode == "protocol"`: Use existing [build_experiment_steps()](cci:1://file://wsl.localhost/Ubuntu/home/alex/backend-interview/backend/app/api/simulations/protocols.py:12:0-91:13) from protocols.py
- If `experiment_mode == "custom"`: Use new `build_experiment_from_definition()`
- If `experiment_mode == "template"`: Fetch template from DB, convert to definition, then build

### 2.4 New Routes for Experiment Management

**File: `backend/app/api/experiments/__init__.py`** (new module)

```python
# Routes for:
# - CRUD for experiment_steps
# - CRUD for experiment_templates  
# - CRUD for drive_cycles
# - GET /experiments/validate - Validate experiment definition
# - GET /experiments/preview - Preview what steps will be generated
```

---

## 3. Frontend UI Changes

### 3.1 New Component: `ExperimentBuilder.tsx`

A visual experiment builder with:
- **Step palette**: Drag-and-drop step types (Current, C-rate, Voltage, Power, Rest, Hold)
- **Cycle builder**: Group steps into cycles, set repeat count
- **String mode toggle**: Switch between visual builder and raw string input
- **Drive cycle uploader**: Upload CSV/JSON for custom drive cycles
- **Preview panel**: Show generated PyBAMM code

### 3.2 Update [SimulationDashboard.tsx](cci:7://file://wsl.localhost/Ubuntu/home/alex/backend-interview/frontend/src/components/SimulationDashboard.tsx:0:0-0:0)

Add to the "New Simulation" dialog:

```tsx
// New state
const [experimentMode, setExperimentMode] = useState<'protocol' | 'custom' | 'template'>('protocol')
const [experimentDefinition, setExperimentDefinition] = useState<ExperimentDefinition | null>(null)
const [experimentTemplateId, setExperimentTemplateId] = useState<string>('')

// New UI section in dialog:
<Grid item xs={12}>
  <FormControl fullWidth>
    <InputLabel>Experiment Mode</InputLabel>
    <Select value={experimentMode} onChange={...}>
      <MenuItem value="protocol">Standard Protocol</MenuItem>
      <MenuItem value="custom">Custom Experiment</MenuItem>
      <MenuItem value="template">From Template</MenuItem>
    </Select>
  </FormControl>
</Grid>

{experimentMode === 'protocol' && (
  // Existing protocol selector
)}

{experimentMode === 'custom' && (
  <ExperimentBuilder 
    value={experimentDefinition}
    onChange={setExperimentDefinition}
  />
)}

{experimentMode === 'template' && (
  <TemplateSelector 
    value={experimentTemplateId}
    onChange={setExperimentTemplateId}
  />
)}
```

### 3.3 New Component: `DriveCycleManager.tsx`

- List available drive cycles (system + user)
- Upload custom drive cycles (CSV format: time_s, value)
- Preview drive cycle as chart
- Select for use in experiments

### 3.4 Update Redux Slice

Add to [simulationsSlice.ts](cci:7://file://wsl.localhost/Ubuntu/home/alex/backend-interview/frontend/src/redux/slices/simulationsSlice.ts:0:0-0:0):
```typescript
export type ExperimentMode = 'protocol' | 'custom' | 'template'

export interface ExperimentStep {
  step_type: 'current' | 'c_rate' | 'voltage' | 'power' | 'resistance' | 'rest' | 'string'
  value?: number
  duration?: string
  termination?: string
  period?: string
  temperature?: string
  tags?: string[]
  step_string?: string
  drive_cycle_data?: number[][]
}

// ... update CreateSimulationParams
```

### 3.5 Update API Service ([api.ts](cci:7://file://wsl.localhost/Ubuntu/home/alex/backend-interview/frontend/src/services/api.ts:0:0-0:0))

```typescript
export const experimentsApi = {
  // Experiment steps CRUD
  getSteps: async () => { ... },
  createStep: async (step: ExperimentStep) => { ... },
  
  // Templates CRUD
  getTemplates: async () => { ... },
  createTemplate: async (template: ExperimentTemplate) => { ... },
  
  // Drive cycles
  getDriveCycles: async () => { ... },
  uploadDriveCycle: async (file: File, metadata: DriveCycleMetadata) => { ... },
  
  // Validation
  validateExperiment: async (definition: ExperimentDefinition) => { ... },
}
```

---

## 4. Implementation Order

| Phase | Tasks | Files |
|-------|-------|-------|
| **Phase 1: Database** | Create migration for new tables | `supabase/migrations/20240107000000_experiment_mode.sql` |
| **Phase 2: Backend Core** | Add schemas, experiment builder | [schemas.py](cci:7://file://wsl.localhost/Ubuntu/home/alex/backend-interview/backend/app/api/presets/schemas.py:0:0-0:0), `experiment_builder.py` |
| **Phase 3: Backend Routes** | Update simulation routes, add experiment routes | [routes.py](cci:7://file://wsl.localhost/Ubuntu/home/alex/backend-interview/backend/app/api/presets/routes.py:0:0-0:0), new `experiments/` module |
| **Phase 4: Frontend Types** | Update TypeScript types, Redux slice | [simulationsSlice.ts](cci:7://file://wsl.localhost/Ubuntu/home/alex/backend-interview/frontend/src/redux/slices/simulationsSlice.ts:0:0-0:0), [api.ts](cci:7://file://wsl.localhost/Ubuntu/home/alex/backend-interview/frontend/src/services/api.ts:0:0-0:0) |
| **Phase 5: Frontend UI** | Build ExperimentBuilder component | `ExperimentBuilder.tsx` |
| **Phase 6: Integration** | Update SimulationDashboard, testing | [SimulationDashboard.tsx](cci:7://file://wsl.localhost/Ubuntu/home/alex/backend-interview/frontend/src/components/SimulationDashboard.tsx:0:0-0:0) |

---

## 5. Summary of New Files

| File | Purpose |
|------|---------|
| `supabase/migrations/20240107000000_experiment_mode.sql` | New tables + columns |
| `backend/app/api/simulations/experiment_builder.py` | Convert definitions to PyBAMM |
| `backend/app/api/experiments/__init__.py` | New experiments router |
| `backend/app/api/experiments/routes.py` | CRUD endpoints |
| `backend/app/api/experiments/schemas.py` | Pydantic models |
| `frontend/src/components/ExperimentBuilder.tsx` | Visual experiment builder |
| `frontend/src/components/DriveCycleManager.tsx` | Drive cycle management |
| `frontend/src/components/TemplateSelector.tsx` | Template selection UI |

---

This plan enables full PyBAMM experiment functionality while maintaining backward compatibility with existing protocol-based simulations. Would you like me to start implementing any specific phase?