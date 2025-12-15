# Tilt configuration for full-stack boilerplate

# Supabase CLI manages the full stack (PostgreSQL, Auth, REST API, Storage, Realtime, Studio)
local_resource(
    'supabase',
    cmd='supabase start',
    deps=['supabase'],
    allow_parallel=True,
)

# Backend - Build Docker image and deploy to Kubernetes
docker_build(
    'backend',
    './backend',
    dockerfile='./backend/Dockerfile',
    live_update=[
        sync('./backend/app', '/app/app'),
        sync('./backend/pyproject.toml', '/app/pyproject.toml'),
        run('poetry install --no-dev --no-interaction --no-ansi', trigger=['./backend/pyproject.toml']),
    ],
)

k8s_yaml('./k8s/backend.yaml')

k8s_resource(
    'backend',
    port_forwards=8000,
    resource_deps=['supabase'],
)

# Frontend - Build Docker image and deploy to Kubernetes
docker_build(
    'frontend',
    './frontend',
    dockerfile='./frontend/Dockerfile',
    live_update=[
        sync('./frontend/src', '/app/src'),
        sync('./frontend/index.html', '/app/index.html'),
        sync('./frontend/vite.config.ts', '/app/vite.config.ts'),
        sync('./frontend/tsconfig.json', '/app/tsconfig.json'),
        sync('./frontend/package.json', '/app/package.json'),
        run('npm install', trigger=['./frontend/package.json']),
    ],
)

k8s_yaml('./k8s/frontend.yaml')

k8s_resource(
    'frontend',
    port_forwards=5173,
    resource_deps=['backend'],
)
