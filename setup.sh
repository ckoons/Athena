#!/bin/bash

# Athena Setup Script
# Creates a virtual environment and installs dependencies for Athena

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# ANSI color codes
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
NC="\033[0m" # No Color

echo -e "${GREEN}Setting up Athena...${NC}"

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed or not in the PATH${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Athena in development mode
echo -e "${YELLOW}Installing Athena and dependencies...${NC}"
pip install -e .

# Install Neo4j driver if possible
echo -e "${YELLOW}Attempting to install Neo4j dependencies...${NC}"
if pip install -e ".[neo4j]" --quiet; then
    echo -e "${GREEN}Installed Neo4j dependencies${NC}"
else
    echo -e "${YELLOW}Could not install Neo4j dependencies. Using memory adapter.${NC}"
fi

# Install development dependencies
pip install pytest pytest-asyncio

# Create data directory
mkdir -p ~/.tekton/data/athena

echo -e "${GREEN}Athena setup complete!${NC}"
echo -e "To activate the virtual environment, run:\n  source venv/bin/activate\n"
