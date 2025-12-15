FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Configure Poetry to not create virtualenvs (install to system Python)
RUN poetry config virtualenvs.create false

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies using Poetry
# --no-root: Don't install the package itself, only dependencies
# Poetry will resolve and install dependencies from pyproject.toml
RUN poetry install --no-dev --no-interaction --no-ansi --no-root

# Copy application code (will be synced by Tilt for hot reload)
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Run the application with reload for development
CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]

