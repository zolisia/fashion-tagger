#!/bin/bash

# Activate virtual environment
source .venv/bin/activate

# Start uvicorn in the background
uvicorn main:app --port 8000 &
UVICORN_PID=$!

# Wait for server to boot
sleep 2

# Open browser
open http://localhost:8000

# Keep script running to maintain uvicorn process
wait $UVICORN_PID