#!/bin/bash
# Start the lightweight OCR server

PORT=${1:-8080}

echo "Starting OCR server on port $PORT..."
./venv/bin/uvicorn server:app --host 0.0.0.0 --port $PORT
