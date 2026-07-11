#!/bin/bash

# Exit immediately if any command fails
set -e

echo "🚀 Starting Transcriberio..."

# 1. Automatically build virtual environment folder if it doesn't exist yet
if [ ! -d ".venv" ]; then
    echo "📦 Creating local Python virtual environment (.venv)..."
    python3 -m venv .venv
fi

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Quietly ensure all dependencies are completely up to date
echo "📥 Syncing project libraries..."
pip install -q -r requirements.txt

# 4. Spin up the application UI server
echo "🖥️  Launching browser dashboard..."
python converter.py
