from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import todos

app = FastAPI(
    title="Ionworks Backend Interview API",
    description="FastAPI backend with Supabase integration",
    version="0.1.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(todos.router, prefix="/api/todos", tags=["todos"])


@app.get("/")
async def root():
    return {"message": "FastAPI backend is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}

