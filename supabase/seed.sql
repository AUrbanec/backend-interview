-- Seed data for local development
-- This creates a demo user for testing

-- Enable pgcrypto extension for password hashing
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Insert demo user into auth.users
-- Note: This bypasses Supabase Auth, so use only for local development
-- Check if user already exists before inserting
DO $$
DECLARE
    user_id UUID;
BEGIN
    -- Check if user already exists
    SELECT id INTO user_id FROM auth.users WHERE email = 'demo@ionworks.com';
    
    -- If user doesn't exist, create it
    IF user_id IS NULL THEN
        INSERT INTO auth.users (
            instance_id,
            id,
            aud,
            role,
            email,
            encrypted_password,
            email_confirmed_at,
            recovery_sent_at,
            last_sign_in_at,
            raw_app_meta_data,
            raw_user_meta_data,
            created_at,
            updated_at,
            confirmation_token,
            email_change,
            email_change_token_new,
            recovery_token
        ) VALUES (
            '00000000-0000-0000-0000-000000000000',  -- default instance_id
            gen_random_uuid(),
            'authenticated',
            'authenticated',
            'demo@ionworks.com',
            crypt('password', gen_salt('bf', 10)),
            NOW(),
            NOW(),
            NOW(),
            '{"provider":"email","providers":["email"]}',
            '{"full_name":"Demo User"}',
            NOW(),
            NOW(),
            '',
            '',
            '',
            ''
        ) RETURNING id INTO user_id;
    END IF;
END $$;

-- Insert the corresponding identity into auth.identities
-- Check if identity already exists before inserting
INSERT INTO auth.identities (
    id,
    user_id,
    provider_id,
    provider,
    identity_data,
    last_sign_in_at,
    created_at,
    updated_at
)
SELECT 
    gen_random_uuid(),
    id,
    id::text,
    'email',
    json_build_object('sub', id::text, 'email', email),
    NOW(),
    NOW(),
    NOW()
FROM auth.users
WHERE email = 'demo@ionworks.com'
  AND NOT EXISTS (
    SELECT 1 FROM auth.identities 
    WHERE user_id = auth.users.id AND provider = 'email'
  );

-- The trigger should automatically create the profile, but we can also ensure it exists
INSERT INTO public.profiles (id, email, full_name)
SELECT 
    id,
    email,
    COALESCE(raw_user_meta_data->>'full_name', 'Demo User')
FROM auth.users
WHERE email = 'demo@ionworks.com'
ON CONFLICT (id) DO UPDATE
SET 
    email = EXCLUDED.email,
    full_name = EXCLUDED.full_name;
