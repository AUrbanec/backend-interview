-- Add missing increment_simulation_count function

CREATE OR REPLACE FUNCTION public.increment_simulation_count(uid UUID)
RETURNS INTEGER AS $$
DECLARE
    current_count INTEGER;
BEGIN
    -- Get current count and increment
    UPDATE public.usage_tracking 
    SET simulations_count = simulations_count + 1,
        updated_at = NOW()
    WHERE user_id = uid
    RETURNING simulations_count INTO current_count;
    
    -- If no row was updated, create one with count 1
    IF current_count IS NULL THEN
        INSERT INTO public.usage_tracking (user_id, simulations_count)
        VALUES (uid, 1)
        RETURNING simulations_count INTO current_count;
    END IF;
    
    RETURN current_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION public.increment_simulation_count(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.increment_simulation_count(UUID) TO service_role;
