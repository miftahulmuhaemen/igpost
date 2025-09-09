# igpost

FastAPI service for uploading videos to Instagram using instagrapi.

## Features
- Upload videos via HTTP API
- Get account profile information
- Session persistence for authentication
- Docker support with Alpine Linux

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
- video: (file) Video file to upload
- description: (string) Caption for the post
- username: (string, optional) Instagram username
- password: (string, optional) Instagram password  
- session_id: (string, optional) Instagram session ID
- session_file: (string, optional) Session file path (default: session.json)
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

## API Examples

### Upload with username/password
```bash
curl -X POST http://localhost:8000/upload \
  -F "video=@/path/to/video.mp4" \
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