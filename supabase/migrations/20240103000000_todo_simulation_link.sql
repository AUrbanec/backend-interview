-- Add optional simulation link to todos table

-- Add simulation_id column to todos table
ALTER TABLE public.todos 
ADD COLUMN simulation_id UUID REFERENCES public.simulations(id) ON DELETE SET NULL;

-- Create index for faster lookups
CREATE INDEX idx_todos_simulation_id ON public.todos(simulation_id);

-- Update RLS policy to allow viewing linked simulation info
-- (The existing policies already handle user access)
