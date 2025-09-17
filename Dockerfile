FROM python:3.11-slim

# Install system dependencies for Pillow, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies separately for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY ./src ./src
COPY ./monitoring ./monitoring
COPY ./configs ./configs

# Create non-root user and switch to it
RUN useradd -m appuser
USER appuser

# Expose API port
EXPOSE 8000

# Entrypoint and default command
ENTRYPOINT ["uvicorn"]
CMD ["src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
