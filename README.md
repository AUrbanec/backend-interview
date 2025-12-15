# Ionworks Backend Interview Boilerplate

A full-stack boilerplate with Tilt orchestration, local Supabase, React frontend with Redux Toolkit and MUI, and FastAPI backend.

## Architecture

- **Frontend**: React + TypeScript + Vite + Redux Toolkit + Material-UI
- **Backend**: FastAPI + Python + Supabase Python Client
- **Database**: Supabase full stack (PostgreSQL, Auth, REST API, Storage, Realtime) running locally via Supabase CLI
- **Orchestration**: Tilt for local development

## Prerequisites

- [Docker](https://www.docker.com/) (required for Supabase CLI)
- [Supabase CLI](https://supabase.com/docs/guides/cli) installed
- [Tilt](https://tilt.dev/) installed
- Python 3.11+ (for backend)
- Node.js 18+ (for frontend)

## Setup

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd backend-interview
   ```

2. **Initialize Supabase** (first time only):
   ```bash
   supabase init
   ```
   
   This ensures the `supabase/` directory is properly initialized.

3. **Start all services with Tilt**:
   ```bash
   tilt up
   ```
   
   This will start:
   - Supabase full stack (via CLI) on port 54321 (API), 54322 (DB), 54323 (Studio)
   - FastAPI backend on port 8000
   - React frontend on port 5173
   
   Tilt will automatically run `supabase start` which:
   - Starts all Supabase services (PostgreSQL, Auth, REST API, Storage, Realtime, Studio)
   - Applies migrations from `supabase/migrations/`
   - Uses the configuration from `supabase/config.toml`
   
   **Note**: The first time you run `supabase start`, it will download Docker images and may take a few minutes.



## Project Structure

```
ionworks-interview-boilerplate/
├── frontend/          # React application
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── redux/         # Redux store and slices
│   │   ├── services/      # API clients
│   │   └── App.tsx
│   └── package.json
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── models/       # Database models
│   │   └── main.py
│   └── pyproject.toml
├── supabase/         # Supabase configuration
│   ├── config.toml
│   └── migrations/   # Database migrations
│   └── seed.sql/     # Database migrations
└── Tiltfile          # Tilt orchestration config
```

## Features

- **Authentication**: Sign up, sign in, and sign out with Supabase Auth
- **Protected Routes**: React Router with authentication guards
- **State Management**: Redux Toolkit with async thunks
- **UI Components**: Material-UI with theme configuration
- **API Integration**: FastAPI endpoints that use Supabase client
- **Todo Example**: Full CRUD operations for todos

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Sign up a new user
- `POST /api/auth/signin` - Sign in an existing user
- `POST /api/auth/signout` - Sign out the current user
- `GET /api/auth/me` - Get current user information

### Todos
- `GET /api/todos/` - Get all todos for the current user
- `POST /api/todos/` - Create a new todo
- `GET /api/todos/{id}` - Get a specific todo
- `PUT /api/todos/{id}` - Update a todo
- `DELETE /api/todos/{id}` - Delete a todo

## Development

### Adding New Features

1. **Backend**: Add new routes in `backend/app/api/`
2. **Frontend**: Add new Redux slices in `frontend/src/redux/slices/`
3. **Database**: Add migrations in `supabase/migrations/`

### Hot Reloading

Tilt automatically reloads services when files change. For manual development:
- Backend: Uses `uvicorn --reload`
- Frontend: Uses Vite's HMR

## Troubleshooting

### Supabase Connection Issues
- Ensure Docker is running (Supabase CLI uses Docker)
- Check Supabase status: `supabase status`
- Verify Supabase is running: `supabase start`
- Check logs: `supabase logs`
- If Supabase fails to start, try: `supabase stop` then `supabase start`

### Port Conflicts
- Change ports in `supabase/config.toml` if needed:
  - API: 54321
  - DB: 54322
  - Studio: 54323
- Update the hardcoded values in `Tiltfile` accordingly
- Restart Supabase: `supabase stop && supabase start`

### Database Migrations
- Migrations are automatically applied when Supabase starts
- Create new migration: `supabase migration new <migration_name>`
- Apply migrations manually: `supabase db reset`
- Check migration status: `supabase migration list`

## License

MIT

