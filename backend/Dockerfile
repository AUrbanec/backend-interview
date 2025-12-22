FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app

# Install system dependencies and uv in a single layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip --no-cache-dir \
    && pip install uv --no-cache-dir

# Copy dependency files
COPY pyproject.toml ./

# Create minimal app structure for package installation
RUN mkdir -p app && touch app/__init__.py

# Install dependencies from pyproject.toml using uv
# uv pip install reads dependencies from the [project] section
RUN uv pip install --system .

# Copy application code (will be synced by Tilt for hot reload)
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Run the application with reload for development
CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
