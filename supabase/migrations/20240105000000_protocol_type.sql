-- Protocol Type Migration
-- Adds protocol_type enum and column for chemistry-aware experiment protocols

-- Create protocol_type enum
CREATE TYPE protocol_type AS ENUM (
    'standard_cycle',
    'capacity_check', 
    'rate_capability',
    'drive_cycle',
    'hppc',
    'custom'
);

-- Add protocol column to simulations table
ALTER TABLE public.simulations 
ADD COLUMN protocol protocol_type DEFAULT 'standard_cycle';

-- Add index for protocol queries (e.g., "show all HPPC tests")
CREATE INDEX idx_simulations_protocol ON public.simulations(protocol);

-- Optional: Add composite index for common queries
CREATE INDEX idx_simulations_user_protocol ON public.simulations(user_id, protocol);
