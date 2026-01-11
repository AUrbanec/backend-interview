-- PyBAMM Experiment Mode Migration
-- Adds support for custom experiment definitions, templates, and drive cycles

-- ============================================================================
-- 1. Experiment Steps Table - Reusable step definitions
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.experiment_steps (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    name TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    
    -- Step definition
    step_type TEXT NOT NULL CHECK (step_type IN ('current', 'c_rate', 'voltage', 'power', 'resistance', 'rest', 'string')),
    value NUMERIC,            -- For current/c_rate/voltage/power/resistance
    value_unit TEXT,          -- 'A', 'C', 'V', 'W', 'Ohm'
    
    -- Duration and termination
    duration TEXT,            -- e.g., '1 hour', '30 minutes', '3600 seconds'
    termination TEXT,         -- e.g., '3.3V', 'C/50', '50mA'
    
    -- Additional options
    period TEXT,              -- Sampling period, e.g., '1 minute'
    temperature TEXT,         -- Step-specific temperature, e.g., '25oC'
    tags TEXT[],              -- Tags for filtering/analysis
    direction TEXT CHECK (direction IN ('charge', 'discharge', NULL)),
    
    -- For string-based steps
    step_string TEXT,         -- Raw string like "Discharge at 1C until 3.3V"
    
    -- For drive cycles (stored as JSON array of [time, value] pairs)
    drive_cycle_data JSONB,
    drive_cycle_type TEXT CHECK (drive_cycle_type IN ('current', 'power', 'voltage', NULL)),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    
    UNIQUE(user_id, name)
);

-- ============================================================================
-- 2. Experiment Templates Table - Collections of steps grouped into cycles
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.experiment_templates (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    name TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    
    -- Experiment structure (array of cycle definitions)
    -- Each cycle contains: { steps: [...], repeat: number }
    cycles JSONB NOT NULL DEFAULT '[]',
    
    -- Default settings
    default_period TEXT DEFAULT '1 minute',
    default_temperature_celsius NUMERIC(5,2) DEFAULT 25.0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    
    UNIQUE(user_id, name)
);

-- ============================================================================
-- 3. Drive Cycles Table - Standard profiles (WLTP, UDDS, custom)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.drive_cycles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),  -- NULL = system preset
    name TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT TRUE,
    
    -- Drive cycle data
    cycle_type TEXT NOT NULL CHECK (cycle_type IN ('current', 'power', 'voltage')),
    data JSONB NOT NULL,       -- Array of [time_s, value] pairs
    duration_seconds NUMERIC,
    
    -- Metadata
    source TEXT,               -- e.g., 'EPA', 'custom', 'WLTP'
    tags TEXT[],
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- ============================================================================
-- 4. Add experiment columns to simulations table
-- ============================================================================
ALTER TABLE public.simulations 
ADD COLUMN IF NOT EXISTS experiment_mode TEXT DEFAULT 'protocol' 
    CHECK (experiment_mode IN ('protocol', 'custom', 'template'));

ALTER TABLE public.simulations 
ADD COLUMN IF NOT EXISTS experiment_definition JSONB;

ALTER TABLE public.simulations 
ADD COLUMN IF NOT EXISTS experiment_template_id UUID REFERENCES public.experiment_templates(id);

ALTER TABLE public.simulations 
ADD COLUMN IF NOT EXISTS experiment_period TEXT DEFAULT '1 minute';

-- ============================================================================
-- 5. Add experiment columns to parameter_presets table
-- ============================================================================
ALTER TABLE public.parameter_presets 
ADD COLUMN IF NOT EXISTS experiment_mode TEXT DEFAULT 'protocol'
    CHECK (experiment_mode IN ('protocol', 'custom', 'template'));

ALTER TABLE public.parameter_presets 
ADD COLUMN IF NOT EXISTS experiment_definition JSONB;

ALTER TABLE public.parameter_presets 
ADD COLUMN IF NOT EXISTS experiment_template_id UUID REFERENCES public.experiment_templates(id);

-- ============================================================================
-- 6. Indexes for performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_experiment_steps_user ON public.experiment_steps(user_id);
CREATE INDEX IF NOT EXISTS idx_experiment_steps_public ON public.experiment_steps(is_public) WHERE is_public = TRUE;
CREATE INDEX IF NOT EXISTS idx_experiment_steps_type ON public.experiment_steps(step_type);

CREATE INDEX IF NOT EXISTS idx_experiment_templates_user ON public.experiment_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_experiment_templates_public ON public.experiment_templates(is_public) WHERE is_public = TRUE;

CREATE INDEX IF NOT EXISTS idx_drive_cycles_user ON public.drive_cycles(user_id);
CREATE INDEX IF NOT EXISTS idx_drive_cycles_public ON public.drive_cycles(is_public) WHERE is_public = TRUE;
CREATE INDEX IF NOT EXISTS idx_drive_cycles_type ON public.drive_cycles(cycle_type);

CREATE INDEX IF NOT EXISTS idx_simulations_experiment_mode ON public.simulations(experiment_mode);
CREATE INDEX IF NOT EXISTS idx_simulations_experiment_template ON public.simulations(experiment_template_id);

-- ============================================================================
-- 7. Enable RLS on new tables
-- ============================================================================
ALTER TABLE public.experiment_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.experiment_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.drive_cycles ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- 8. RLS Policies for experiment_steps
-- ============================================================================
CREATE POLICY "Users can view own steps and public steps"
    ON public.experiment_steps FOR SELECT
    USING (auth.uid() = user_id OR is_public = TRUE OR user_id IS NULL);

CREATE POLICY "Users can create own steps"
    ON public.experiment_steps FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own steps"
    ON public.experiment_steps FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own steps"
    ON public.experiment_steps FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- 9. RLS Policies for experiment_templates
-- ============================================================================
CREATE POLICY "Users can view own templates and public templates"
    ON public.experiment_templates FOR SELECT
    USING (auth.uid() = user_id OR is_public = TRUE OR user_id IS NULL);

CREATE POLICY "Users can create own templates"
    ON public.experiment_templates FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own templates"
    ON public.experiment_templates FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own templates"
    ON public.experiment_templates FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- 10. RLS Policies for drive_cycles
-- ============================================================================
CREATE POLICY "Users can view own cycles and public cycles"
    ON public.drive_cycles FOR SELECT
    USING (auth.uid() = user_id OR is_public = TRUE OR user_id IS NULL);

CREATE POLICY "Users can create own cycles"
    ON public.drive_cycles FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own cycles"
    ON public.drive_cycles FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own cycles"
    ON public.drive_cycles FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================================
-- 11. Insert default system experiment templates
-- ============================================================================
INSERT INTO public.experiment_templates (user_id, name, description, is_public, cycles, default_period) VALUES
    -- Standard CCCV cycle template
    (NULL, 'CCCV Standard Cycle', 'Standard constant-current constant-voltage charge followed by CC discharge', TRUE,
     '[{"steps": [
        {"step_type": "string", "step_string": "Discharge at 1C until 3.0V"},
        {"step_type": "string", "step_string": "Rest for 10 minutes"},
        {"step_type": "string", "step_string": "Charge at 0.5C until 4.2V"},
        {"step_type": "string", "step_string": "Hold at 4.2V until C/50"},
        {"step_type": "string", "step_string": "Rest for 10 minutes"}
     ], "repeat": 1}]'::jsonb, '1 minute'),
    
    -- Capacity check template
    (NULL, 'Capacity Check (C/20)', 'Slow discharge for accurate capacity measurement', TRUE,
     '[{"steps": [
        {"step_type": "string", "step_string": "Charge at 0.5C until 4.2V"},
        {"step_type": "string", "step_string": "Hold at 4.2V until C/50"},
        {"step_type": "string", "step_string": "Rest for 1 hour"},
        {"step_type": "string", "step_string": "Discharge at C/20 until 2.5V"},
        {"step_type": "string", "step_string": "Rest for 1 hour"}
     ], "repeat": 1}]'::jsonb, '1 minute'),
    
    -- Formation cycling template
    (NULL, 'Formation Cycle (3x)', 'Three formation cycles at low rate', TRUE,
     '[{"steps": [
        {"step_type": "string", "step_string": "Charge at C/10 until 4.2V"},
        {"step_type": "string", "step_string": "Hold at 4.2V until C/50"},
        {"step_type": "string", "step_string": "Rest for 30 minutes"},
        {"step_type": "string", "step_string": "Discharge at C/10 until 2.5V"},
        {"step_type": "string", "step_string": "Rest for 30 minutes"}
     ], "repeat": 3}]'::jsonb, '1 minute'),
    
    -- HPPC template
    (NULL, 'HPPC Pulse Test', 'Hybrid pulse power characterization for resistance measurement', TRUE,
     '[{"steps": [
        {"step_type": "string", "step_string": "Charge at 1C until 4.2V"},
        {"step_type": "string", "step_string": "Hold at 4.2V until C/50"},
        {"step_type": "string", "step_string": "Rest for 1 hour"}
     ], "repeat": 1},
     {"steps": [
        {"step_type": "string", "step_string": "Discharge at 1C for 10 seconds"},
        {"step_type": "string", "step_string": "Rest for 40 seconds"},
        {"step_type": "string", "step_string": "Charge at 0.75C for 10 seconds"},
        {"step_type": "string", "step_string": "Rest for 1 hour"},
        {"step_type": "string", "step_string": "Discharge at 1C for 360 seconds"},
        {"step_type": "string", "step_string": "Rest for 1 hour"}
     ], "repeat": 9}]'::jsonb, '1 second'),
    
    -- Rate capability template
    (NULL, 'Rate Capability Test', 'Discharge at increasing C-rates', TRUE,
     '[{"steps": [
        {"step_type": "string", "step_string": "Charge at 0.5C until 4.2V"},
        {"step_type": "string", "step_string": "Hold at 4.2V until C/50"},
        {"step_type": "string", "step_string": "Rest for 30 minutes"},
        {"step_type": "string", "step_string": "Discharge at 0.2C until 2.5V"},
        {"step_type": "string", "step_string": "Rest for 30 minutes"}
     ], "repeat": 1},
     {"steps": [
        {"step_type": "string", "step_string": "Charge at 0.5C until 4.2V"},
        {"step_type": "string", "step_string": "Hold at 4.2V until C/50"},
        {"step_type": "string", "step_string": "Rest for 30 minutes"},
        {"step_type": "string", "step_string": "Discharge at 0.5C until 2.5V"},
        {"step_type": "string", "step_string": "Rest for 30 minutes"}
     ], "repeat": 1},
     {"steps": [
        {"step_type": "string", "step_string": "Charge at 0.5C until 4.2V"},
        {"step_type": "string", "step_string": "Hold at 4.2V until C/50"},
        {"step_type": "string", "step_string": "Rest for 30 minutes"},
        {"step_type": "string", "step_string": "Discharge at 1C until 2.5V"},
        {"step_type": "string", "step_string": "Rest for 30 minutes"}
     ], "repeat": 1},
     {"steps": [
        {"step_type": "string", "step_string": "Charge at 0.5C until 4.2V"},
        {"step_type": "string", "step_string": "Hold at 4.2V until C/50"},
        {"step_type": "string", "step_string": "Rest for 30 minutes"},
        {"step_type": "string", "step_string": "Discharge at 2C until 2.5V"},
        {"step_type": "string", "step_string": "Rest for 30 minutes"}
     ], "repeat": 1}]'::jsonb, '1 minute')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 12. Insert sample drive cycles
-- ============================================================================
INSERT INTO public.drive_cycles (user_id, name, description, is_public, cycle_type, data, duration_seconds, source, tags) VALUES
    -- Simplified urban drive cycle (10 second pattern)
    (NULL, 'Urban Pulse Cycle', 'Simplified urban driving pattern with acceleration/deceleration pulses', TRUE,
     'current',
     '[[0, 0], [1, 0.5], [2, 1.0], [3, 1.5], [4, 1.0], [5, 0.5], [6, 0], [7, -0.3], [8, 0], [9, 0.2], [10, 0]]'::jsonb,
     10, 'custom', ARRAY['urban', 'pulse']),
    
    -- Simple discharge ramp
    (NULL, 'Discharge Ramp', 'Linear ramp from 0.5C to 2C over 60 seconds', TRUE,
     'current',
     '[[0, 0.5], [15, 0.875], [30, 1.25], [45, 1.625], [60, 2.0]]'::jsonb,
     60, 'custom', ARRAY['ramp', 'stress-test']),
    
    -- Sinusoidal current profile
    (NULL, 'Sinusoidal Profile', 'Sinusoidal current variation for impedance-like testing', TRUE,
     'current',
     '[[0, 0], [0.5, 0.31], [1, 0.59], [1.5, 0.81], [2, 0.95], [2.5, 1.0], [3, 0.95], [3.5, 0.81], [4, 0.59], [4.5, 0.31], [5, 0], [5.5, -0.31], [6, -0.59], [6.5, -0.81], [7, -0.95], [7.5, -1.0], [8, -0.95], [8.5, -0.81], [9, -0.59], [9.5, -0.31], [10, 0]]'::jsonb,
     10, 'custom', ARRAY['sinusoidal', 'impedance'])
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 13. Comments on new columns and tables
-- ============================================================================
COMMENT ON TABLE public.experiment_steps IS 'Reusable experiment step definitions for PyBAMM experiments';
COMMENT ON TABLE public.experiment_templates IS 'Experiment templates containing cycles of steps';
COMMENT ON TABLE public.drive_cycles IS 'Drive cycle profiles (time-varying current/power/voltage)';

COMMENT ON COLUMN public.simulations.experiment_mode IS 'Mode: protocol (predefined), custom (user-defined steps), template (from template)';
COMMENT ON COLUMN public.simulations.experiment_definition IS 'Custom experiment definition when experiment_mode=custom';
COMMENT ON COLUMN public.simulations.experiment_template_id IS 'Reference to experiment template when experiment_mode=template';
COMMENT ON COLUMN public.simulations.experiment_period IS 'Sampling period for experiment steps (e.g., 1 minute)';
