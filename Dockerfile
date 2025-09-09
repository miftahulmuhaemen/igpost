# Alpine-based image
FROM python:3.11-alpine

# Install system deps (build and runtime)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    ffmpeg \
    jpeg-dev \
    zlib-dev

WORKDIR /app
COPY . /app

# Install project
RUN pip install --no-cache-dir -e .

# Default environment
ENV IGPOST_SESSION_FILE=/state/session.json \
    IGPOST_VERBOSE=true

# Expose API port
EXPOSE 8000

# Create mount point for state
VOLUME ["/state"]

# Run API with Uvicorn
CMD ["uvicorn", "igpost.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
