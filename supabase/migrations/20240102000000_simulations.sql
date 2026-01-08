-- Battery Simulations Feature Migration

-- Simulation status enum
CREATE TYPE simulation_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');

-- Battery chemistry enum
CREATE TYPE battery_chemistry AS ENUM ('LFP', 'NMC', 'NCA', 'LCO', 'custom');

-- Simulations table - stores battery simulation jobs and results
CREATE TABLE IF NOT EXISTS public.simulations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    status simulation_status DEFAULT 'pending' NOT NULL,
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    
    -- Simulation parameters
    chemistry battery_chemistry DEFAULT 'LFP' NOT NULL,
    c_rate NUMERIC(5,2) DEFAULT 1.0 NOT NULL,
    temperature_celsius NUMERIC(5,2) DEFAULT 25.0 NOT NULL,
    cycles INTEGER DEFAULT 1 CHECK (cycles >= 1 AND cycles <= 1000),
    
    -- Custom parameters (JSON for flexibility)
    custom_parameters JSONB DEFAULT '{}',
    
    -- Results (stored as JSON for flexibility with PyBaMM output)
    results JSONB,
    error_message TEXT,
    
    -- Timing
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Parameter presets table - reusable simulation configurations
CREATE TABLE IF NOT EXISTS public.parameter_presets (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),  -- NULL means system preset (shared)
    name TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    
    -- Preset parameters
    chemistry battery_chemistry DEFAULT 'LFP' NOT NULL,
    c_rate NUMERIC(5,2) DEFAULT 1.0 NOT NULL,
    temperature_celsius NUMERIC(5,2) DEFAULT 25.0 NOT NULL,
    cycles INTEGER DEFAULT 1,
    custom_parameters JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    
    UNIQUE(user_id, name)
);

-- Usage tracking table - tracks API usage for rate limiting
CREATE TABLE IF NOT EXISTS public.usage_tracking (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    
    -- Usage counters (reset monthly)
    simulations_count INTEGER DEFAULT 0,
    simulations_limit INTEGER DEFAULT 100,  -- Monthly limit
    api_calls_count INTEGER DEFAULT 0,
    api_calls_limit INTEGER DEFAULT 10000,  -- Monthly limit
    
    -- Current billing period
    period_start TIMESTAMP WITH TIME ZONE DEFAULT date_trunc('month', NOW()) NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE DEFAULT date_trunc('month', NOW()) + INTERVAL '1 month' NOT NULL,
    
    -- Timestamps
    last_simulation_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    
    UNIQUE(user_id, period_start)
);

-- API call logs for detailed tracking
CREATE TABLE IF NOT EXISTS public.api_call_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Indexes for performance
CREATE INDEX idx_simulations_user_id ON public.simulations(user_id);
CREATE INDEX idx_simulations_status ON public.simulations(status);
CREATE INDEX idx_simulations_created_at ON public.simulations(created_at DESC);
CREATE INDEX idx_parameter_presets_user_id ON public.parameter_presets(user_id);
CREATE INDEX idx_parameter_presets_public ON public.parameter_presets(is_public) WHERE is_public = TRUE;
CREATE INDEX idx_usage_tracking_user_period ON public.usage_tracking(user_id, period_start);
CREATE INDEX idx_api_call_logs_user_id ON public.api_call_logs(user_id);
CREATE INDEX idx_api_call_logs_created_at ON public.api_call_logs(created_at DESC);

-- Enable RLS on all tables
ALTER TABLE public.simulations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parameter_presets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_call_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies for simulations
CREATE POLICY "Users can view own simulations"
    ON public.simulations FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create own simulations"
    ON public.simulations FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own simulations"
    ON public.simulations FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own simulations"
    ON public.simulations FOR DELETE
    USING (auth.uid() = user_id);

-- RLS Policies for parameter_presets
CREATE POLICY "Users can view own presets"
    ON public.parameter_presets FOR SELECT
    USING (auth.uid() = user_id OR is_public = TRUE OR user_id IS NULL);

CREATE POLICY "Users can create own presets"
    ON public.parameter_presets FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own presets"
    ON public.parameter_presets FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own presets"
    ON public.parameter_presets FOR DELETE
    USING (auth.uid() = user_id);

-- RLS Policies for usage_tracking
CREATE POLICY "Users can view own usage"
    ON public.usage_tracking FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own usage"
    ON public.usage_tracking FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own usage"
    ON public.usage_tracking FOR UPDATE
    USING (auth.uid() = user_id);

-- RLS Policies for api_call_logs
CREATE POLICY "Users can view own logs"
    ON public.api_call_logs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own logs"
    ON public.api_call_logs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Function to auto-create usage tracking record for new users
CREATE OR REPLACE FUNCTION public.handle_new_user_usage()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.usage_tracking (user_id)
    VALUES (NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger for auto-creating usage tracking
CREATE TRIGGER on_auth_user_created_usage
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user_usage();

-- Insert default system presets
INSERT INTO public.parameter_presets (user_id, name, description, is_public, chemistry, c_rate, temperature_celsius, cycles) VALUES
    (NULL, 'LFP Standard', 'Standard LFP battery at 1C rate, 25°C', TRUE, 'LFP', 1.0, 25.0, 1),
    (NULL, 'LFP Fast Charge', 'LFP battery at 2C rate for fast charging analysis', TRUE, 'LFP', 2.0, 25.0, 1),
    (NULL, 'NMC Standard', 'Standard NMC battery at 1C rate, 25°C', TRUE, 'NMC', 1.0, 25.0, 1),
    (NULL, 'NMC High Temp', 'NMC battery at elevated temperature (40°C)', TRUE, 'NMC', 1.0, 40.0, 1),
    (NULL, 'NCA Standard', 'Standard NCA battery at 1C rate, 25°C', TRUE, 'NCA', 1.0, 25.0, 1),
    (NULL, 'Cycle Life Test', 'Multi-cycle degradation test (10 cycles)', TRUE, 'LFP', 1.0, 25.0, 10);
