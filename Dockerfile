# Build stage
FROM python:3.11-slim AS builder
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir .

# Runtime stage - Slim (has python3 in PATH)
FROM python:3.11-slim
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
WORKDIR /app
EXPOSE 8000
VOLUME ["/sessions"]
CMD ["python3", "-m", "uvicorn", "igpost.api.app:app", "--host", "0.0.0.0", "--port", "8000"]