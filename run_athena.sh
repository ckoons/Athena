#!/bin/bash

# Athena Launch Script
# Starts the Athena Knowledge Graph API server

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# ANSI color codes
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Default port
PORT=${ATHENA_PORT:-8005}

# Check if port is in use
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${RED}Error: Port $PORT is already in use. Please specify a different port with ATHENA_PORT env variable.${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Running setup script...${NC}"
    ./setup.sh
fi

# Activate virtual environment
source venv/bin/activate

echo -e "${GREEN}Starting Athena Knowledge Graph server on port $PORT...${NC}"

# Set environment variables
export ATHENA_PORT=$PORT

# Start the server
uvicorn athena.api.app:app --host 0.0.0.0 --port $PORT --reload

# Note: This script will keep running until the server is stopped with Ctrl+C