# igpost

FastAPI service for uploading videos to Instagram using instagrapi.

## Features
- Upload videos via HTTP API
- Get account profile information
- Session persistence for authentication
- Docker support with Alpine Linux

## Prerequisites
- Python 3.9+
- `uv` installed (recommended) or `pip`

## API Endpoints

### Health Check
```bash
GET /health
```

### Get Profile
```bash
GET /profile?username=your_user&password=your_pass
# OR
GET /profile?session_id=your_session_id
```

### Upload Video
```bash
POST /upload
Content-Type: multipart/form-data

Fields:
- video: (file, optional) Video file to upload (binary)
- video_path: (string, optional) Path to video file on server
- description: (string) Caption for the post
- username: (string, optional) Instagram username
- password: (string, optional) Instagram password  
- session_id: (string, optional) Instagram session ID
- session_file: (string, optional) Session file path (default: session.json)

Note: Provide either 'video' (file upload) or 'video_path' (server path), not both.
```

## Local Development

### Using uv (Recommended)
```bash
# Install dependencies
uv sync

# Run the service
uv run uvicorn igpost.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### Using pip
```bash
# Install dependencies
pip install -e .

# Run the service
uvicorn igpost.api.app:app --host 0.0.0.0 --port 8000 --reload
```

## Docker Usage

### Build and Run
```bash
# Build image
docker build -t igpost:latest .

# Run container
docker run -p 8000:8000 -v ./sessions:/sessions igpost:latest
```

### Docker Compose
```bash
docker compose up --build -d
```

### Windows Volume Mounting
The docker-compose.yml includes a volume mount for Windows:
- Windows C: drive is mounted as `/uploads` (read-only)
- Access Windows files via `/uploads/Users/username/...`
- Example: `/uploads/Users/john/Videos/myvideo.mp4`

## API Examples

### Upload with binary file
```bash
curl -X POST http://localhost:8000/upload \
  -F "video=@/path/to/video.mp4" \
  -F "description=My awesome video" \
  -F "username=your_username" \
  -F "password=your_password"
```

### Upload with file path (mounted volume)
```bash
curl -X POST http://localhost:8000/upload \
  -F "video_path=/uploads/Users/me/Videos/video.mp4" \
  -F "description=My awesome video" \
  -F "username=your_username" \
  -F "password=your_password"
```

### Upload with session ID
```bash
curl -X POST http://localhost:8000/upload \
  -F "video=@/path/to/video.mp4" \
  -F "description=My awesome video" \
  -F "session_id=your_session_id"
```

### Get profile
```bash
curl "http://localhost:8000/profile?username=your_user&password=your_pass"
```

## Authentication Priority
1. **Session ID** (if provided) - fastest, no re-authentication
2. **Username/Password** (if provided) - creates new session

## Session Persistence
- Sessions are automatically saved to `/sessions/session.json` in the container
- Mount `./sessions:/sessions` to persist sessions between container restarts
- Each session can be reused for multiple uploads

## Library Reference
- [instagrapi on GitHub](https://github.com/subzeroid/instagrapi)

## Current Issues
- Python 3.11-alpine base image
- Multiple build dependencies (gcc, musl-dev, etc.)
- FFmpeg and media libraries
- All dependencies installed

## Solutions to Reduce Image Size

### 1. **Multi-stage Build (Recommended)**
```dockerfile
# Build stage
FROM python:3.11-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    jpeg-dev \
    zlib-dev

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -e .

# Runtime stage
FROM python:3.11-alpine AS runtime

# Install only runtime dependencies
RUN apk add --no-cache \
    ffmpeg \
    jpeg-dev \
    zlib-dev

# Copy only the built package
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/src /app/src

WORKDIR /app
EXPOSE 8000
VOLUME ["/sessions"]
CMD ["uvicorn", "igpost.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. **Use Slim Base Image**
```dockerfile
FROM python:3.11-slim

# Install only what's needed
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -e .

EXPOSE 8000
VOLUME ["/sessions"]
CMD ["uvicorn", "igpost.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. **Minimal Alpine with Cleanup**
```dockerfile
FROM python:3.11-alpine

# Install everything in one layer and clean up
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    ffmpeg \
    jpeg-dev \
    zlib-dev \
    && pip install --no-cache-dir instagrapi fastapi uvicorn python-multipart \
    && apk del gcc musl-dev libffi-dev openssl-dev \
    && rm -rf /var/cache/apk/*

WORKDIR /app
COPY src/ /app/src/
COPY pyproject.toml /app/

EXPOSE 8000
VOLUME ["/sessions"]
CMD ["uvicorn", "igpost.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4. **Distroless Image (Smallest)**
```dockerfile
<code_block_to_apply_changes_from>
```

## Expected Size Reduction
- **Current**: ~700MB
- **Multi-stage Alpine**: ~150-200MB
- **Slim**: ~200-300MB
- **Distroless**: ~100-150MB

## Quick Fix
Try the multi-stage build first - it should reduce your image to ~150-200MB while keeping all functionality.

Which approach would you like me to implement?