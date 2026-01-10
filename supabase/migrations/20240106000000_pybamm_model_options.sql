-- PyBAMM Model Options Migration
-- Adds model_type and model_options columns to support full PyBAMM model customization

-- Add model_type column for selecting PyBAMM model (SPM, SPMe, DFN, MPM, etc.)
ALTER TABLE public.simulations 
ADD COLUMN IF NOT EXISTS model_type TEXT DEFAULT 'DFN';

-- Add model_options column for advanced PyBAMM options (SEI, lithium plating, particle, etc.)
ALTER TABLE public.simulations 
ADD COLUMN IF NOT EXISTS model_options JSONB DEFAULT '{}';

-- Add same columns to parameter_presets for storing preset configurations
ALTER TABLE public.parameter_presets 
ADD COLUMN IF NOT EXISTS model_type TEXT DEFAULT 'DFN';

ALTER TABLE public.parameter_presets 
ADD COLUMN IF NOT EXISTS model_options JSONB DEFAULT '{}';

-- Add index for model_type queries
CREATE INDEX IF NOT EXISTS idx_simulations_model_type ON public.simulations(model_type);

-- Update existing system presets with model_type
UPDATE public.parameter_presets 
SET model_type = 'DFN', model_options = '{}'
WHERE model_type IS NULL;

-- Add some advanced system presets showcasing different models and options
INSERT INTO public.parameter_presets (
    user_id, name, description, is_public, chemistry, c_rate, temperature_celsius, cycles, 
    model_type, model_options
) VALUES
    -- SPM presets (faster)
    (NULL, 'SPM Fast Screen', 'Fast SPM model for quick parameter screening', TRUE, 'NMC', 1.0, 25.0, 1,
     'SPM', '{"thermal": "isothermal", "particle": "uniform profile"}'),
    
    -- SPMe presets (balanced)
    (NULL, 'SPMe Standard', 'SPMe model with electrolyte dynamics', TRUE, 'NMC', 1.0, 25.0, 1,
     'SPMe', '{"thermal": "isothermal"}'),
    
    -- DFN with thermal
    (NULL, 'DFN Thermal Analysis', 'Full DFN with lumped thermal model', TRUE, 'NMC', 2.0, 25.0, 3,
     'DFN', '{"thermal": "lumped"}'),
    
    -- DFN with SEI
    (NULL, 'DFN SEI Growth', 'DFN model with SEI degradation', TRUE, 'NMC', 1.0, 35.0, 10,
     'DFN', '{"thermal": "lumped", "SEI": "solvent-diffusion limited", "SEI porosity change": "true"}'),
    
    -- DFN with lithium plating
    (NULL, 'DFN Li Plating', 'DFN model for lithium plating analysis at low temp', TRUE, 'NMC', 1.0, 0.0, 5,
     'DFN', '{"thermal": "lumped", "lithium plating": "partially reversible"}'),
    
    -- DFN with particle mechanics
    (NULL, 'DFN Mechanical Stress', 'DFN model with particle swelling and cracking', TRUE, 'NMC', 2.0, 25.0, 20,
     'DFN', '{"thermal": "lumped", "particle mechanics": "swelling and cracking", "loss of active material": "stress-driven"}')
ON CONFLICT DO NOTHING;

-- Comment on new columns
COMMENT ON COLUMN public.simulations.model_type IS 'PyBAMM model type: SPM, SPMe, DFN, MPM, NewmanTobias, MSMR';
COMMENT ON COLUMN public.simulations.model_options IS 'Advanced PyBAMM model options: thermal, SEI, lithium_plating, particle, etc.';
COMMENT ON COLUMN public.parameter_presets.model_type IS 'PyBAMM model type for this preset';
COMMENT ON COLUMN public.parameter_presets.model_options IS 'Advanced PyBAMM model options for this preset';
